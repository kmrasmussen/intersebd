import os
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import PlainTextResponse  # Import PlainTextResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
import uuid

from database import get_db
from models import AgentWidget
from config import settings  # Make sure settings are imported

logger = logging.getLogger(__name__)

# --- Constants ---
WIDGET_JS_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'widget', 'companya', 'brainy_widget_functionality.js')

# --- Request and Response Models ---

class NewWidgetRequest(BaseModel):
    user_id: Optional[str] = None
    origin: str
    tools: List[Dict[str, Any]]

class NewWidgetResponse(BaseModel):
    widget_id: uuid.UUID
    origin: str
    tools: List[Dict[str, Any]]
    user_id: Optional[str] = None
    message: str

    class Config:
        from_attributes = True

class AgentWidgetRequestPayload(BaseModel):
    widget_id: uuid.UUID
    previous_response_id: Optional[str] = None
    input: List[Dict[str, Any]]
    model: str = Field(default="gpt-4.1-nano", description="Optional: Specify the OpenAI model to use")

# --- Router Definition ---
router = APIRouter(
    prefix='/api/agent-widgets',
    tags=["Agent Widgets"],
)

# --- OpenAI Client Setup ---
if not settings.openai_api_key:
    logger.warning("OPENAI_API_KEY environment variable not set. /agent_widget_request endpoint will fail.")

# --- API Endpoints ---

@router.post('/new_widget',
             response_model=NewWidgetResponse,
             status_code=status.HTTP_201_CREATED)
async def create_new_widget(
    widget_data: NewWidgetRequest,
    session: AsyncSession = Depends(get_db)
):
    user_id = widget_data.user_id

    new_widget = AgentWidget(
        user_id=user_id,
        cors_origin=widget_data.origin,
        tools=widget_data.tools,
        is_active=True
    )

    try:
        session.add(new_widget)
        await session.commit()
        await session.refresh(new_widget)
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

@router.get('/{widget_id}/widget.js',
            response_class=PlainTextResponse)
async def get_widget_script(widget_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """
    Serves the brainy_widget_functionality.js script with the
    correct WIDGET_ID and API_ENDPOINT injected.
    """
    stmt = select(AgentWidget.id).where(AgentWidget.id == widget_id)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    try:
        with open(WIDGET_JS_TEMPLATE_PATH, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        logger.error(f"Widget JS template not found at: {WIDGET_JS_TEMPLATE_PATH}")
        raise HTTPException(status_code=500, detail="Widget script template missing")

    # --- Construct the dynamic API endpoint URL ---
    api_path = "/api/cors-anywhere/agent_widget_request"
    full_api_endpoint = f"{settings.backend_base_url.rstrip('/')}{api_path}"
    logger.debug(f"Injecting API Endpoint: {full_api_endpoint}")

    # Replace placeholders
    script_content = template_content.replace("__WIDGET_ID_PLACEHOLDER__", str(widget_id))
    script_content = script_content.replace("__API_ENDPOINT_PLACEHOLDER__", full_api_endpoint)

    # Return as JavaScript
    return PlainTextResponse(content=script_content, media_type="application/javascript")

@router.post('/cors-anywhere/agent_widget_request')
async def agent_widget_request(
    payload: AgentWidgetRequestPayload,
    session: AsyncSession = Depends(get_db)
):
    if not settings.openai_api_key:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured on the server."
        )

    stmt = select(AgentWidget).where(AgentWidget.id == payload.widget_id, AgentWidget.is_active == True)
    result = await session.execute(stmt)
    widget = result.scalar_one_or_none()

    if not widget:
        logger.warning(f"Agent widget request failed: Widget ID {payload.widget_id} not found or inactive.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent Widget with ID {payload.widget_id} not found or is inactive."
        )

    openai_payload = {
        "model": payload.model,
        "input": payload.input,
        "tools": widget.tools
    }
    if payload.previous_response_id:
        openai_payload["previous_response_id"] = payload.previous_response_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}"
    }

    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Calling OpenAI Responses API for widget {widget.id}. Payload: {openai_payload}")
            openai_response = await client.post(
                settings.openai_api_url,
                headers=headers,
                json=openai_payload,
                timeout=60.0
            )
            await openai_response.aread()

        except httpx.RequestError as e:
            logger.error(f"Error calling OpenAI API for widget {widget.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to OpenAI API: {e}"
            )
        except Exception as e:
             logger.error(f"Unexpected error during OpenAI call for widget {widget.id}: {e}", exc_info=True)
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request."
            )

    response_headers = {
        "Content-Type": openai_response.headers.get("Content-Type", "application/json")
    }

    return Response(
        content=openai_response.content,
        status_code=openai_response.status_code,
        headers=response_headers
    )
