from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import httpx
import json
import os
from datetime import datetime
import logging
import uvicorn
from typing import Optional, Dict, Any, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, engine, Base
from models import *
from utils import *
import hashlib
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text # Import text for potential raw SQL needs if array_agg index fails
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles # Import StaticFiles
from sqlalchemy.orm import selectinload, joinedload # Ensure selectinload and joinedload are imported
from sqlalchemy.exc import SQLAlchemyError # Import SQLAlchemyError

# imports from solution
from auth import router as auth_router
from provider_keys import router as provider_keys_router
from completion_alternatives import router as completion_alternatives_router
from agent_widget import router as agent_widget_router # Import the new router
from corsanywhere import cors_anywhere_app # Import the CORS Anywhere app
from annotation import router as annotation_router
from config import settings
from finetuning import router as finetuning_router
from nextmockingrouter import router as nextmocking_router
from completion_projects import router as completion_projects_router
from completion_project_call_keys import router as completion_project_call_keys_router

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Ensure level is DEBUG
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(title="intercebd-backend", version="0.1.0",  swagger_ui_parameters={"persistAuthorization": True})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

'''
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

'''
# Add this debug print:
print(f"DEBUG: Configuring CORS with allow_origins=['{settings.frontend_base_url}'] and allow_credentials=True")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

'''
from middleware import EnforceStrictCORSPostMiddleware
logger.info(f"Adding EnforceStrictCORSPostMiddleware for strict origins: {[settings.frontend_base_url]}")
app.add_middleware(
    EnforceStrictCORSPostMiddleware,
    strict_origins=[settings.frontend_base_url], # Pass the STRICT list here
    public_path_prefix="/api/cors-anywhere" # The path prefix for the permissive sub-app
)
'''

app.add_middleware(
   SessionMiddleware,
   secret_key=settings.session_secret_key,
)

app.include_router(auth_router)  
app.include_router(provider_keys_router)
app.include_router(completion_alternatives_router)
app.include_router(agent_widget_router) # Include the new router
app.include_router(annotation_router)
app.include_router(finetuning_router)
app.include_router(nextmocking_router)
app.include_router(completion_projects_router)
app.include_router(completion_project_call_keys_router)

app.mount("/api/cors-anywhere", cors_anywhere_app)

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "statically_served")
app.mount("/static", StaticFiles(directory=static_dir), name="static_files")

# Directory to store request logs
LOGS_DIR = "request_logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# OpenAI API base URL
OPENAI_API_BASE = "https://api.openai.com"
OPENROUTER_CHAT_COMPLETIONS_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


# Create a shared httpx client to reuse connections
http_client = httpx.AsyncClient(timeout=60.0)

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

class CompletionsAnnotationRequestDto(BaseModel):
   completion_response_id: str
   rater_id: Optional[str] = None
   reward: Optional[float] = None
   annotation_metadata : Optional[Dict] = None
   intercept_key: str

class CompletionsAnnotationResponseDto(BaseModel):
    annotation_id: str
    status: str
    message: str

@app.post("/v1/chat/completions/annotation", response_model=CompletionsAnnotationResponseDto)
async def create_annotation(request: CompletionsAnnotationRequestDto, session: AsyncSession = Depends(get_db)):
    # verify that a completion response with that id exists
    stmt = (
        select(CompletionResponse)
        # Only need to load the related CompletionsRequest
        .options(selectinload(CompletionResponse.completion_request))
        .where(CompletionResponse.id == request.completion_response_id)
    )
    result = await session.execute(stmt)
    # Use unique() for potential future complex queries, good practice
    completion_response = result.unique().scalar_one_or_none()

    if not completion_response:
        logger.warning(f"CompletionResponse not found: {request.completion_response_id}")
        raise HTTPException(status_code=404, detail="Completion response not found")

    # Check if the related completion_request was loaded
    if not completion_response.completion_request:
         logger.error(f"Data integrity issue: Missing completion_request for CompletionResponse ID: {request.completion_response_id}")
         raise HTTPException(status_code=500, detail="Associated request data not found")

    # Access intercept_key directly from completion_request
    if completion_response.completion_request.intercept_key != request.intercept_key:
        logger.warning(f"Intercept key mismatch for CompletionResponse ID: {request.completion_response_id}. Expected {completion_response.completion_request.intercept_key}, got {request.intercept_key}")
        raise HTTPException(status_code=403, detail="Intercept key mismatch")

    annotation = CompletionAnnotation(
        completion_id=request.completion_response_id,
        rater_id=request.rater_id,
        reward=request.reward,
        annotation_metadata=request.annotation_metadata
    )

    session.add(annotation)
    await session.commit()
    await session.refresh(annotation)

    logger.info(f"Annotation created successfully with ID: {annotation.id}")

    return CompletionsAnnotationResponseDto(
        annotation_id=str(annotation.id),
        status="success",
        message="Annotation created successfully"
    )

class CompletionsRaterNotificationRequestDto(BaseModel):
    rater_id: str
    content: Optional[str] = None
    completion_response_id: str
    intercept_key: uuid.UUID

    class Config:
        from_attributes = True

class CompletionsRaterNotificationResponseDto(BaseModel):
    notification_id: str
    status: str
    message: str

@app.post("/v1/chat/completions/rater/notifications", response_model=CompletionsRaterNotificationResponseDto)
async def create_rater_notification(request: CompletionsRaterNotificationRequestDto):
    print('got to the rater notifcaitons endpoint!')
    try:
    
      if not request.rater_id or not request.completion_response_id or not request.intercept_key:
          raise HTTPException(status_code=400, detail="Missing required fields")

      # Create a new notification entry
      notification = CompletionsRaterNotification(
          rater_id=request.rater_id,
          content=request.content,
          completion_response_id=request.completion_response_id,
          intercept_key=request.intercept_key
      )

      # Save to database
      async for session in get_db():
          session.add(notification)
          await session.commit()  
          return CompletionsRaterNotificationResponseDto(
              notification_id=str(notification.id),
              status="success",
              message="Notification created successfully",
              timestamp=notification.timestamp
          )
    except Exception as e:
      logger.error(f"Error creating notification: {e}")
      raise HTTPException(status_code=500, detail="Internal server error while creating notification.")

class CompletionChoiceDetailDto(BaseModel):
  index: int
  finish_reason: Optional[str] = None
  role: Optional[str] = None
  content: Optional[str] = None

  class Config:
      from_attributes = True 

class CompletionResponseDetailDto(BaseModel):
  id: str
  provider: Optional[str] = None
  model: Optional[str] = None
  created: Optional[int] = None
  prompt_tokens: Optional[int] = None
  completion_tokens: Optional[int] = None
  total_tokens: Optional[int] = None
  choices: List[CompletionChoiceDetailDto] = [] # Include choices here

  class Config:
    from_attributes = True # Ensure this line is present and correct

class UniqueMessageGroup(BaseModel):
  messages_hash: str
  messages: List[Dict[str, Any]]
  count: int

  class Config:
    from_attributes = True

class CompletionsRequestDetailDto(BaseModel):
  messages: List[Dict[str, Any]]
  messages_hash: str
  model: Optional[str] = None
  response_format: Optional[Dict[str, Any]] = None # Assuming response_format is JSONB/dict
  response_format_hash: Optional[str] = None

  class Config:
      from_attributes = True

class RaterNotificationDetailsResponseDto(BaseModel):
  notification: CompletionsRaterNotificationRequestDto # Re-use or create specific DTO
  completion_request: Optional[CompletionsRequestDetailDto] = None
  completion_response: Optional[CompletionResponseDetailDto] = None
  class Config:
    from_attributes = True

# ... existing code ...

@app.get("/v1/chat/completions/rater/notifications/{notification_id}/details", response_model=RaterNotificationDetailsResponseDto)
async def get_rater_notification_details(notification_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching details for notification ID: {notification_id}")
    try:
        # 1. Fetch the notification
        stmt_notification = select(CompletionsRaterNotification).where(CompletionsRaterNotification.id == notification_id)
        result_notification = await session.execute(stmt_notification)
        notification = result_notification.scalar_one_or_none()

        if not notification:
            logger.warning(f"Notification not found: {notification_id}")
            raise HTTPException(status_code=404, detail="Notification not found")

        logger.info(f"Found notification. Fetching related completion response ID: {notification.completion_response_id}")

        # 2. Fetch the CompletionResponse and its Choices using the ID from the notification
        # Use joinedload for choices as it's a one-to-many relationship often needed together
        stmt_response = (
            select(CompletionResponse)
            .options(joinedload(CompletionResponse.choices)) # Eager load choices
            .where(CompletionResponse.id == notification.completion_response_id)
        )
        result_response = await session.execute(stmt_response)
        completion_response = result_response.unique().scalar_one_or_none() # Use unique() because of joinedload

        if not completion_response:
            # This indicates a potential data integrity issue if a notification exists without a response
            logger.error(f"CompletionResponse not found for ID: {notification.completion_response_id}, but notification {notification_id} exists.")
            raise HTTPException(status_code=404, detail="Associated Completion Response not found")

        logger.info(f"Found completion response. Fetching related request log ID: {completion_response.request_log_id}")

        # 3. Fetch the CompletionsRequest using the request_log_id from the CompletionResponse
        stmt_request = select(CompletionsRequest).where(CompletionsRequest.request_log_id == completion_response.request_log_id)
        result_request = await session.execute(stmt_request)
        completion_request = result_request.scalar_one_or_none()

        if not completion_request:
            # This also indicates a potential data integrity issue
            logger.error(f"CompletionsRequest not found for request_log_id: {completion_response.request_log_id}")
            # Decide if this should be a 404 or maybe return partial data
            raise HTTPException(status_code=404, detail="Associated Completion Request not found")

        logger.info(f"Found completion request. Assembling response.")

        # 4. Assemble the response DTO
        # Map SQLAlchemy models to Pydantic DTOs
        response_dto = RaterNotificationDetailsResponseDto(
            notification=CompletionsRaterNotificationRequestDto.from_orm(notification), # Map notification
            completion_request=CompletionsRequestDetailDto.from_orm(completion_request), # Map request
            completion_response=CompletionResponseDetailDto.from_orm(completion_response) # Map response (includes choices)
        )

        return response_dto

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        logger.exception(f"Error fetching notification details for {notification_id}: {e}", exc_info=True) # Log full traceback
        raise HTTPException(status_code=500, detail="Internal server error while fetching notification details.")

class CompletionsNotificationsListRequestDto(BaseModel):
    intercept_key: uuid.UUID
    rater_id: str

class CompletionsRaterNotificationsListItemResponseDto(BaseModel):
  rater_id: str
  content: Optional[str] = None
  completion_response_id: str
  intercept_key: uuid.UUID
  timestamp: datetime
  class Config:
      from_attributes = True

class CompletionsNotificationsListResponseDto(BaseModel):
    notifications: List[CompletionsRaterNotificationsListItemResponseDto]

    class Config:
        from_attributes = True 
# ... rest of the file ...
 
@app.post("/v1/chat/completions/rater/notifications/list", response_model=CompletionsNotificationsListResponseDto)
async def list_rater_notifications(request: CompletionsNotificationsListRequestDto, session: AsyncSession = Depends(get_db)):
    logger.info(f"Listing notifications for rater ID: {request.rater_id} and intercept key: {request.intercept_key}")
    try:
        stmt = (
            select(CompletionsRaterNotification)
            .where(
                CompletionsRaterNotification.rater_id == request.rater_id,
                CompletionsRaterNotification.intercept_key == request.intercept_key
            )
        )
        result = await session.execute(stmt)
        notifications = result.scalars().all()

        if not notifications:
            logger.warning(f"No notifications found for rater ID: {request.rater_id} and intercept key: {request.intercept_key}")
            raise HTTPException(status_code=404, detail="No notifications found")

        response_dto = CompletionsNotificationsListResponseDto(
            notifications=[CompletionsRaterNotificationsListItemResponseDto.from_orm(notification) for notification in notifications]
        )

        return response_dto

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        logger.exception(f"Error listing notifications for rater ID: {request.rater_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while listing notifications.")


@app.api_route("/v1/chat/completions", methods=["POST"])
async def proxy(request: Request, session: AsyncSession = Depends(get_db)): # Get session via Depends

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("accept-encoding", None)
    auth_header = headers.get("authorization", "")
    project_call_key_value = None
    if auth_header.lower().startswith("bearer "):
        project_call_key_value = auth_header[7:]
    else:
        logger.warning(f"Invalid or missing Authorization header format: {auth_header}")
        raise HTTPException(status_code=401, detail="Invalid Authorization header format.")

    if not project_call_key_value:
        raise HTTPException(status_code=401, detail="Authorization token missing.")

    project_id_for_request: Optional[uuid.UUID] = None # Variable to store the project ID
    linked_or_key_value: Optional[str] = None # Variable to store the OR key

    try:
        # Find the CompletionProjectCallKeys record and its linked OpenRouterGuestKey
        stmt = (
            select(CompletionProjectCallKeys)
            .options(selectinload(CompletionProjectCallKeys.openrouter_guest_key))
            .where(CompletionProjectCallKeys.key == project_call_key_value)
        )
        result = await session.execute(stmt)
        project_call_key_record = result.scalars().first()

        if not project_call_key_record:
            logger.warning(f"Project Call Key not found: {project_call_key_value}")
            raise HTTPException(status_code=401, detail="Invalid API Key provided.")

        if not project_call_key_record.is_active:
            logger.warning(f"Project Call Key is inactive: {project_call_key_value}")
            raise HTTPException(status_code=403, detail="API Key is inactive.")

        # --- Get the Project ID ---
        project_id_for_request = project_call_key_record.project_id
        if not project_id_for_request:
             logger.error(f"Project Call Key {project_call_key_value} has no associated project_id.")
             raise HTTPException(status_code=500, detail="Internal configuration error: API key not linked to a project.")

        linked_or_key = project_call_key_record.openrouter_guest_key

        if not linked_or_key:
            logger.error(f"No OpenRouter key linked to Project Call Key: {project_call_key_value} (ID: {project_call_key_record.id})")
            raise HTTPException(status_code=500, detail="Internal configuration error: No provider key linked to this API key.")

        if not linked_or_key.is_active or linked_or_key.or_disabled:
            logger.warning(f"Linked OpenRouter key is inactive/disabled for Project Call Key: {project_call_key_value}")
            raise HTTPException(status_code=403, detail="Provider key associated with this API key is inactive.")

        linked_or_key_value = linked_or_key.or_key
        headers["authorization"] = f"Bearer {linked_or_key_value}"
        logger.info(f"Using OpenRouter key linked to Project Call Key {project_call_key_value[:5]}... for project {project_id_for_request}")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error during key lookup or processing for Project Call Key {project_call_key_value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error finding or processing API key.")

    target_url = OPENROUTER_CHAT_COMPLETIONS_ENDPOINT

    try:
        # Forward the request to OpenRouter
        async with httpx.AsyncClient() as client:
            logger.debug(f"Forwarding request to {target_url}")
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True
            )

        # --- Database Logging ---
        # Use the session obtained from Depends(get_db)
        try:
            # --- Remove RequestsLog creation ---
            # log_entry = RequestsLog(...)
            # session.add(log_entry)
            # await session.flush()

            if response.status_code == 200:
                try:
                    response_data = json.loads(response.content.decode('utf-8', errors='replace'))
                    body_json_loaded = json.loads(body.decode('utf-8', errors='replace'))

                    request_body_messages = body_json_loaded.get("messages", [])
                    messages_hash = hash_json_content(request_body_messages)
                    request_body_model = body_json_loaded.get("model", "")
                    request_body_response_format = body_json_loaded.get("response_format", None)
                    request_body_response_format_hash = hash_json_content(request_body_response_format) if request_body_response_format is not None else None

                    # --- Create CompletionsRequest with project_id ---
                    completion_request = CompletionsRequest(
                        # request_log_id=log_entry.id, # Removed
                        # intercept_key=project_call_key_value, # Removed
                        project_id=project_id_for_request, # Added
                        messages=request_body_messages,
                        messages_hash=messages_hash,
                        model=request_body_model,
                        response_format=request_body_response_format,
                        response_format_hash=request_body_response_format_hash,
                    )
                    logger.debug(f"Creating CompletionsRequest for project {project_id_for_request}")
                    session.add(completion_request)
                    await session.flush() # Flush to get completion_request.id
                    logger.info(f"Added CompletionsRequest with id {completion_request.id}")

                    choices = response_data.get("choices", [])
                    if not choices:
                         logger.warning("Response from provider contained no 'choices'. Cannot log CompletionResponse.")
                         # Decide how to handle this - maybe commit request only, or raise error?
                         await session.commit() # Commit request even if response is weird
                         # Continue to return response to client below
                    else:
                        first_choice = choices[0]
                        message = first_choice.get("message", {})

                        # Create AnnotationTarget first
                        new_annotation_target = AnnotationTarget()
                        session.add(new_annotation_target)
                        await session.flush() # Flush to get the ID
                        logger.debug(f"Created AnnotationTarget with id {new_annotation_target.id}")

                        # Create CompletionResponse linked to CompletionsRequest and AnnotationTarget
                        completion = CompletionResponse(
                            id=response_data["id"], # Use ID from provider response
                            completion_request_id=completion_request.id, # Link to our request
                            annotation_target_id=new_annotation_target.id, # Link to annotation target
                            provider=response_data.get("provider", ""), # Optional provider field
                            model=response_data.get("model", ""),
                            created=response_data.get("created", 0),
                            prompt_tokens=response_data.get("usage", {}).get("prompt_tokens", 0),
                            completion_tokens=response_data.get("usage", {}).get("completion_tokens", 0),
                            total_tokens=response_data.get("usage", {}).get("total_tokens", 0),
                            choice_finish_reason=first_choice.get("finish_reason", ""),
                            choice_role=message.get("role", ""),
                            choice_content=message.get("content", "")
                        )
                        session.add(completion)
                        logger.info(f"Added CompletionResponse with id {completion.id}")

                        await session.commit() # Commit request, target, and response together
                        logger.debug("Committed CompletionsRequest, AnnotationTarget, and CompletionResponse.")

                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to decode JSON from request body or provider response: {json_err}")
                    # Decide how to handle - maybe raise 500, or just log and skip structured logging
                    await session.rollback() # Rollback any partial adds
                except KeyError as key_err:
                     logger.error(f"Missing expected key in provider response data: {key_err}", exc_info=True)
                     await session.rollback()
                except Exception as e:
                    logger.error(f"Error storing structured response data: {e}", exc_info=True)
                    await session.rollback() # Rollback on any other error during structured logging
            else:
                 # Log non-200 responses? Currently only logging 200s structurally.
                 logger.info(f"Received non-200 status ({response.status_code}) from provider. Skipping structured logging.")
                 # No commit needed here if nothing was added

        except SQLAlchemyError as db_exc:
            logger.error(f"Database error during logging for project {project_id_for_request}: {db_exc}", exc_info=True)
            await session.rollback() # Ensure rollback on DB error
            # Do not raise HTTPException here, as we still want to return the provider's response
        except Exception as log_exc:
             logger.error(f"Unexpected error during logging setup for project {project_id_for_request}: {log_exc}", exc_info=True)
             await session.rollback() # Rollback just in case

        # Prepare headers for the response back to the original client
        response_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in [
                'content-encoding', 'transfer-encoding', 'connection', 'content-length',
            ]
        }

        # Return the response to the client
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers
        )

    except httpx.RequestError as exc:
        logger.error(f"Error making request to OpenRouter: {exc}")
        # Don't try to log to DB here as the request failed
        return JSONResponse(
            status_code=502, # Bad Gateway might be appropriate
            content={"error": f"Error proxying request to provider: {str(exc)}"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in proxy endpoint: {e}", exc_info=True)
        # Don't try to log to DB here
        raise HTTPException(status_code=500, detail="Internal server error during request proxying.")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "openai-proxy"}

@app.get("/stats")
async def get_stats():
    """Get usage statistics"""
    # In the future, implement statistics about API usage
    return {"status": "implemented", "message": "Statistics will be available here"}

#if __name__ == "__main__":
#    uvicorn.run("main:app", host="0.0.0.0", port=9003, reload=True)