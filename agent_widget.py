import os
import json
import httpx # Import httpx for async requests
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response # Added Request, Response
from pydantic import BaseModel, HttpUrl, Field # Added Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # Import select for querying
import logging
import uuid

from database import get_db
from models import AgentWidget
from config import settings
# Assuming you might want to associate widgets with authenticated users eventually
# from auth import get_current_user, UserInfo

logger = logging.getLogger(__name__)

# --- Request and Response Models ---

class NewWidgetRequest(BaseModel):
    user_id: Optional[str] = None # Optional for now, could be linked to auth later
    origin: str # The allowed CORS origin for this widget
    tools: List[Dict[str, Any]] # Define the structure of tools more specifically if needed

class NewWidgetResponse(BaseModel):
    widget_id: uuid.UUID
    origin: str
    tools: List[Dict[str, Any]]
    user_id: Optional[str] = None
    message: str

    class Config:
        from_attributes = True # Use from_attributes instead of orm_mode in Pydantic v2

# --- New Request Model for agent_widget_request ---
class AgentWidgetRequestPayload(BaseModel):
    widget_id: uuid.UUID
    previous_response_id: Optional[str] = None
    input: List[Dict[str, Any]] # Expecting OpenAI input format e.g. [{"role": "user", "content": "..."}]
    model: str = Field(default="gpt-4.1-nano", description="Optional: Specify the OpenAI model to use") # Allow overriding model

# --- Router Definition ---

router = APIRouter(
    prefix='/agent-widgets',
    tags=["Agent Widgets"],
    # dependencies=[Depends(get_current_user)] # Uncomment if authentication is required
)

# --- OpenAI Client Setup ---
# It's better to initialize the client once if possible, or create it per request
# For simplicity here, we'll create it inside the request function


if not settings.openai_api_key:
    logger.warning("OPENAI_API_KEY environment variable not set. /agent_widget_request endpoint will fail.")
    # You might want to raise an error at startup instead, depending on your deployment strategy

# --- API Endpoints ---

@router.post('/new_widget',
             response_model=NewWidgetResponse,
             status_code=status.HTTP_201_CREATED)
async def create_new_widget(
    widget_data: NewWidgetRequest,
    # current_user: UserInfo = Depends(get_current_user), # Uncomment if using auth
    session: AsyncSession = Depends(get_db)
):
    """
    Creates a new Agent Widget configuration.
    """
    # user_id = current_user.sub # Use authenticated user ID if auth is enabled
    user_id = widget_data.user_id # Or take from request body

    new_widget = AgentWidget(
        user_id=user_id,
        cors_origin=widget_data.origin,
        tools=widget_data.tools,
        is_active=True # Default to active
    )

    try:
        session.add(new_widget)
        await session.commit()
        await session.refresh(new_widget) # To get the generated ID and defaults
        logger.info(f"Created new Agent Widget with ID: {new_widget.id} for origin: {new_widget.cors_origin}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating new agent widget: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create agent widget in database."
        )

    return NewWidgetResponse(
        widget_id=new_widget.id,
        origin=new_widget.cors_origin,
        tools=new_widget.tools,
        user_id=new_widget.user_id,
        message="Agent Widget created successfully."
    )

# --- New Endpoint ---
@router.post('/agent_widget_request')
async def agent_widget_request(
    payload: AgentWidgetRequestPayload,
    session: AsyncSession = Depends(get_db)
    # request: Request # Inject FastAPI Request object if you need headers etc. from incoming req
):
    """
    Receives a request for a specific widget, fetches its configuration,
    calls the OpenAI Responses API, and forwards the response.
    """
    if not settings.openai_api_key:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured on the server."
        )

    # 1. Fetch the widget configuration
    stmt = select(AgentWidget).where(AgentWidget.id == payload.widget_id, AgentWidget.is_active == True)
    result = await session.execute(stmt)
    widget = result.scalar_one_or_none()

    if not widget:
        logger.warning(f"Agent widget request failed: Widget ID {payload.widget_id} not found or inactive.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent Widget with ID {payload.widget_id} not found or is inactive."
        )

    # 2. Prepare OpenAI request payload
    openai_payload = {
        "model": payload.model, # Use model from request, defaults to nano
        "input": payload.input,
        "tools": widget.tools # Use tools from the specific widget config
    }
    if payload.previous_response_id:
        openai_payload["previous_response_id"] = payload.previous_response_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}"
    }

    # 3. Make the async request to OpenAI
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Calling OpenAI Responses API for widget {widget.id}. Payload: {openai_payload}")
            openai_response = await client.post(
                settings.openai_api_url,
                headers=headers,
                json=openai_payload,
                timeout=60.0 # Set a reasonable timeout
            )
            # Ensure the response content is read before closing the client context
            # This is important for forwarding the response body correctly
            await openai_response.aread()

        except httpx.RequestError as e:
            logger.error(f"Error calling OpenAI API for widget {widget.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to OpenAI API: {e}"
            )
        except Exception as e: # Catch other potential errors
             logger.error(f"Unexpected error during OpenAI call for widget {widget.id}: {e}", exc_info=True)
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request."
            )

    # 4. Forward the OpenAI response (status, headers, body)
    # Be selective about which headers to forward if necessary,
    # but forwarding content-type is usually important.
    response_headers = {
        "Content-Type": openai_response.headers.get("Content-Type", "application/json")
        # Add any other headers from openai_response you want to forward
    }

    return Response(
        content=openai_response.content,
        status_code=openai_response.status_code,
        headers=response_headers
    )


# You can add more endpoints here later (e.g., get, update, delete widgets)
