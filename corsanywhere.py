import httpx
import logging
import uuid
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Assuming database, models, and settings are accessible from this location
# Adjust imports if your project structure requires it
from database import get_db
from models import AgentWidget
from config import settings

logger = logging.getLogger(__name__)

# --- Pydantic Model for the Request ---
class AgentWidgetRequestPayload(BaseModel):
    widget_id: uuid.UUID
    previous_response_id: Optional[str] = None
    input: List[Dict[str, Any]] # Expecting OpenAI input format e.g. [{"role": "user", "content": "..."}]
    model: str = Field(default="gpt-4.1-nano", description="Optional: Specify the OpenAI model to use")

# --- Initialize the dedicated FastAPI app ---
cors_anywhere_app = FastAPI(
    title="Public Agent Widget Service",
    description="Handles public agent widget requests with permissive CORS"
)

# --- Apply Permissive CORS Middleware ---
cors_anywhere_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True, # Allow credentials (e.g., cookies, auth headers) if needed
    allow_methods=["*"],  # Allow all standard methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# --- OpenAI API Configuration ---
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_URL = "https://api.openai.com/v1/responses"

if not OPENAI_API_KEY:
    logger.error("CRITICAL: OPENAI_API_KEY environment variable not set. /agent_widget_request endpoint WILL fail.")
    # Consider raising an exception here during startup if the key is absolutely essential

# --- API Endpoint Definition ---
@cors_anywhere_app.post('/agent_widget_request')
async def agent_widget_request(
    payload: AgentWidgetRequestPayload,
    request: Request, # Inject Request to get Origin header
    session: AsyncSession = Depends(get_db)
):
    """
    Receives a request for a specific widget, fetches its configuration,
    validates the origin against the DB, calls OpenAI, and forwards the response.
    CORS preflight/response headers are handled by the CORSMiddleware.
    """
    if not OPENAI_API_KEY:
         # This check might be redundant if you raise an error at startup
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key is not configured on the server."
        )

    # 1. Fetch the widget configuration
    stmt = select(AgentWidget).where(AgentWidget.id == payload.widget_id, AgentWidget.is_active == True)
    result = await session.execute(stmt)
    widget = result.scalar_one_or_none()

    if not widget:
        logger.warning(f"Public agent widget request failed: Widget ID {payload.widget_id} not found or inactive.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent Widget with ID {payload.widget_id} not found or is inactive."
        )

    # 2. Validate Origin Header against Database (Still crucial security step)
    origin_header = request.headers.get("origin")

    # Handle OPTIONS preflight requests gracefully - CORSMiddleware does this.
    # This logic runs for the actual POST request.
    if request.method == "POST":
        if not origin_header:
            logger.warning(f"Public agent widget POST request for {widget.id} missing Origin header.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Origin header is required for this request."
            )

        # --- IMPORTANT: Check against the specific origin stored for the widget ---
        if origin_header != widget.cors_origin:
            logger.warning(f"Public agent widget request origin mismatch for {widget.id}. Allowed: '{widget.cors_origin}', Received: '{origin_header}'.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Origin '{origin_header}' is not allowed for this widget."
            )
        # If validation passes, proceed.

    # 3. Prepare OpenAI request payload
    openai_payload = {
        "model": payload.model,
        "input": payload.input,
        "tools": widget.tools
    }
    if payload.previous_response_id:
        openai_payload["previous_response_id"] = payload.previous_response_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # 4. Make the async request to OpenAI
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Calling OpenAI Responses API for public widget {widget.id} from origin {origin_header}. Payload: {openai_payload}")
            openai_response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=openai_payload,
                timeout=60.0
            )
            await openai_response.aread()

        except httpx.RequestError as e:
            logger.error(f"Error calling OpenAI API for public widget {widget.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to OpenAI API: {e}"
            )
        except Exception as e:
             logger.error(f"Unexpected error during OpenAI call for public widget {widget.id}: {e}", exc_info=True)
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request."
            )

    # 5. Forward the OpenAI response
    # CORSMiddleware will add the appropriate Access-Control-Allow-* headers.
    response_headers = {
        "Content-Type": openai_response.headers.get("Content-Type", "application/json"),
    }

    return Response(
        content=openai_response.content,
        status_code=openai_response.status_code,
        headers=response_headers
    )

# Optional: Add a root endpoint for testing the sub-app
@cors_anywhere_app.get("/")
async def read_root():
    return {"message": "CORS Anywhere Agent Widget Service is running"}