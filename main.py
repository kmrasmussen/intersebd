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

# imports from solution
from auth import router as auth_router
from intercept_keys import router as intercept_keys_router, find_openrouter_key_by_intercept_key
from provider_keys import router as provider_keys_router
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Ensure level is DEBUG
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(title="intercebd-backend", version="0.1.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "*",  # Allows all origins - BE CAREFUL IN PRODUCTION!
    # Add your specific frontend origin(s) here for production, e.g.:
    "http://localhost:5173/",
    # "https://yourfrontenddomain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

app.add_middleware(
   SessionMiddleware,
   secret_key=settings.session_secret_key,
)

app.include_router(auth_router)  # Include the auth router
app.include_router(intercept_keys_router)
app.include_router(provider_keys_router)

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
   intercept_key: uuid.UUID

class CompletionsAnnotationResponseDto(BaseModel):
    annotation_id: str
    status: str
    message: str

@app.post("/v1/chat/completions/annotation", response_model=CompletionsAnnotationResponseDto)
async def create_annotation(request: CompletionsAnnotationRequestDto, session: AsyncSession = Depends(get_db)):
    # verify that a completion response with that id exists
    stmt = (
        select(CompletionResponse)
        .options(selectinload(CompletionResponse.request_log)) # Eager load choices
        .where(CompletionResponse.id == request.completion_response_id)
    )
    result = await session.execute(stmt)
    print('createannotation response lookup result', result)
    completion_response = result.scalar_one_or_none()

    if not completion_response:
        logger.warning(f"CompletionResponse not found: {request.completion_response_id}")
        raise HTTPException(status_code=404, detail="Completion response not found")
    
    if completion_response.request_log.intercept_key != request.intercept_key:
        logger.warning(f"Intercept key mismatch for CompletionResponse ID: {request.completion_response_id}. Expected {completion_response.request_log.intercept_key}, got {request.intercept_key}")
        raise HTTPException(status_code=403, detail="Intercept key mismatch")

    annotation = CompletionAnnotation(
        completion_id=request.completion_response_id,
        rater_id=request.rater_id,
        reward=request.reward,
        annotation_metadata=request.annotation_metadata
        # Note: intercept_key is implicitly validated via the completion_response relationship
    )

    session.add(annotation)
    await session.commit()
    await session.refresh(annotation) # To get the generated ID and timestamp

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
        from_attributes = True # Changed from orm_mode

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

from sqlalchemy.orm import selectinload, joinedload # Add joinedload

class CompletionChoiceDetailDto(BaseModel):
  index: int
  finish_reason: Optional[str] = None
  role: Optional[str] = None
  content: Optional[str] = None

  class Config:
      from_attributes = True # Changed from orm_mode

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
    from_attributes = True # Changed from orm_mode

class CompletionsRequestDetailDto(BaseModel):
  messages: List[Dict[str, Any]]
  messages_hash: str
  model: Optional[str] = None
  response_format: Optional[Dict[str, Any]] = None # Assuming response_format is JSONB/dict
  response_format_hash: Optional[str] = None

  class Config:
      from_attributes = True # Changed from orm_mode

class RaterNotificationDetailsResponseDto(BaseModel):
  notification: CompletionsRaterNotificationRequestDto # Re-use or create specific DTO
  completion_request: Optional[CompletionsRequestDetailDto] = None
  completion_response: Optional[CompletionResponseDetailDto] = None
  class Config:
    from_attributes = True # Changed from orm_mode

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
        # Note: Pydantic V2 with orm_mode=True handles much of this automatically if field names match
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
      from_attributes = True # Changed from orm_mode

class CompletionsNotificationsListResponseDto(BaseModel):
    notifications: List[CompletionsRaterNotificationsListItemResponseDto]

    class Config:
        from_attributes = True # Changed from orm_mode
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

@app.get('/intercept/{intercept_key}/unique_request_messages', response_model=List[UniqueMessageGroup])
# Ensure intercept_key is typed as uuid.UUID for validation
async def get_unique_request_messages(intercept_key: uuid.UUID, session: AsyncSession = Depends(get_db)): 
  try: # Add try/except block for better error handling
    stmt = (
      select(
          CompletionsRequest.messages_hash,
          # Aggregate messages into an array and take the first element (PostgreSQL arrays are 1-indexed)
          func.array_agg(CompletionsRequest.messages)[1].label("messages"), 
          func.count(CompletionsRequest.id).label("count") # Count occurrences
      )
      .join(RequestsLog, CompletionsRequest.request_log_id == RequestsLog.id) # Join on the foreign key
      .where(RequestsLog.intercept_key == intercept_key) # Filter by the intercept key
      .group_by(CompletionsRequest.messages_hash) # Group ONLY by the hash
      .order_by(func.count(CompletionsRequest.id).desc()) # Optional: order by frequency
    )
    
    result = await session.execute(stmt)
    grouped_results = result.all() 

    response_data = [
        UniqueMessageGroup(
            messages_hash=row.messages_hash,
            messages=row.messages, # This should now contain the JSON array from the first element
            count=row.count
        )
        for row in grouped_results
    ]
    
    return response_data
  except Exception as e:
      logger.error(f"Error retrieving unique messages for key {intercept_key}: {e}")
      # Consider logging the actual SQL error if available (e.g., e.orig)
      raise HTTPException(status_code=500, detail="Internal server error while retrieving messages.")


@app.api_route("/v1/chat/completions", methods=["POST"])
async def proxy(request: Request, session: AsyncSession = Depends(get_db)):

  body = await request.body()

  print("HEEY")
  
  # Convert headers to dict and filter out host header
  headers = dict(request.headers)
  headers.pop("host", None)
  # Also remove accept-encoding, as the proxy will handle decoding if necessary
  # Let the target server decide how to encode its response
  headers.pop("accept-encoding", None)
  
  auth_header = headers.get("authorization", "")
  api_key = None
  if auth_header.lower().startswith("bearer "):
      api_key = auth_header[7:] # Get the part after "Bearer "
  else:
      # Handle cases where the header is missing or doesn't start with Bearer
      logger.warning(f"Invalid or missing Authorization header format: {auth_header}")
      raise HTTPException(status_code=401, detail="Invalid Authorization header format.")

  if not api_key: # Double check if api_key extraction failed
        raise HTTPException(status_code=401, detail="Authorization token missing.")

  # test raise exception with api key
  #raise HTTPException(status_code=401, detail=f"Test exception with api key, {api_key}")

  try:
    matching_openrouter_key = await find_openrouter_key_by_intercept_key(api_key, session)
    #raise HTTPException(status_code=401, detail=f"Test exception with api key and openrouter, {api_key} and or: {matching_openrouter_key.or_key}")
    if not matching_openrouter_key:
        # Handle case where intercept key is valid but no matching OpenRouter key is found
        raise HTTPException(status_code=401, detail=f"Valid intercept key, but no corresponding OpenRouter key configured: {matching_openrouter_key}")
    # Replace the incoming Authorization header with the found OpenRouter key
    headers["authorization"] = f"Bearer {matching_openrouter_key.or_key}"
    print("Replaced Authorization header with OpenRouter key.")
  except HTTPException as http_exc: # Re-raise specific HTTP exceptions
      raise http_exc
  except Exception as e:
    # Log the actual error for debugging
    logger.error(f"Error during OpenRouter key lookup or processing for intercept key {api_key}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Error finding or processing OpenRouter key")

  # Construct target URL
  target_url = OPENROUTER_CHAT_COMPLETIONS_ENDPOINT #f"{OPENAI_API_BASE}/{path}"
  
  try:
    # Forward the request to OpenRouter
    async with httpx.AsyncClient() as client:
      # Log the headers just before sending the request
      logger.debug(f"Forwarding request to {target_url} with headers: {headers}") # <-- ADD THIS LINE

      response = await client.request(
          method=request.method,
          url=target_url,
          headers=headers, # Ensure this 'headers' dict contains the correct Authorization
          content=body,
          follow_redirects=True
      )

      try:
          # Get a new DB session for this request

        async for session in get_db(): # Use the dependency
            log_entry = RequestsLog(
            intercept_key=api_key,
              request_method=request.method,
              request_url=str(request.url),
              request_headers=dict(request.headers), # Store all headers for now
              request_body=json.loads(body),
              response_status_code=response.status_code,
              response_headers=dict(response.headers),
              response_body=json.loads(response.content.decode('utf-8', errors='replace'))
            )
            print(f"Created log entry: {log_entry}")
            session.add(log_entry)
            print("Added to session")

            await session.flush()
            
            print('Trying to log it more structured too:')                
            # After your existing DB logging code
            if response.status_code == 200:
                try:
                    response_data = json.loads(response.content.decode('utf-8', errors='replace'))
                    
                    # Create completion response record
                    completion = CompletionResponse(
                        id=response_data["id"],
                        request_log_id=log_entry.id,  # Link to the original request log
                        provider=response_data.get("provider", ""),
                        model=response_data.get("model", ""),
                        created=response_data.get("created", 0),
                        prompt_tokens=response_data.get("usage", {}).get("prompt_tokens", 0),
                        completion_tokens=response_data.get("usage", {}).get("completion_tokens", 0),
                        total_tokens=response_data.get("usage", {}).get("total_tokens", 0)
                    )
                    
                    session.add(completion)

                    body_json_loaded = json.loads(body.decode('utf-8', errors='replace'))
                    request_body_messages = body_json_loaded.get("messages", [])
                    print(f"Request body messages: {request_body_messages}")
                    # Hash the messages for storage
                    messages_hash = hash_json_content(request_body_messages)
                    print(f"Messages hash: {messages_hash}")
                    request_body_model = body_json_loaded.get("model", "")
                    print(f"Request body model: {request_body_model}")
                    # Change the default value from "" to None
                    request_body_response_format = body_json_loaded.get("response_format", None) 
                    print('Request body response format:', request_body_response_format)
                    # Hash None as None or handle appropriately if hashing is needed
                    request_body_response_format_hash = hash_json_content(request_body_response_format) if request_body_response_format is not None else None
                    print('making completion request object')
                    completion_request = CompletionsRequest(
                      messages = request_body_messages,
                      messages_hash = messages_hash,
                      model = request_body_model,
                      response_format = request_body_response_format, # Will now store None if not present
                      request_log_id=log_entry.id,  # Link to the original request log
                      response_format_hash= request_body_response_format_hash
                    )
                    print('trying to add completion request')
                    session.add(completion_request)
                    print('added completion request')
                    # Create choice records
                    for idx, choice in enumerate(response_data.get("choices", [])):
                        message = choice.get("message", {})
                        choice_record = CompletionChoice(
                            completion_id=response_data["id"],
                            index=idx,
                            finish_reason=choice.get("finish_reason", ""),
                            role=message.get("role", ""),
                            content=message.get("content", "")
                        )
                        session.add(choice_record)
                    
                    await session.commit()
                    print('committed the structured stuff')
                    
                except Exception as e:
                    logger.error(f"Error storing structured response: {e}")

            # Add an explicit commit here to see if it helps
            await session.commit()
            print("Committed to database")
            print(f"Logged request/response for key {api_key} to DB")

      except Exception as e:
        print(f"Failed to log request to DB for key {api_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to log request to DB")
            # Optionally log to file as fallback here if DB fails

    
    # Prepare headers for the response back to the original client
    # Filter out headers that should not be blindly forwarded
    response_headers = {
        k: v for k, v in response.headers.items()
        if k.lower() not in [
            'content-encoding',
            'transfer-encoding',
            'connection',
            'content-length', # Will be set automatically by FastAPI/Starlette
        ]
    }

    # Return the response to the client
    return Response(
        content=response.content, # Forward the raw content bytes
        status_code=response.status_code,
        headers=response_headers # Forward filtered headers
    )
      
  except httpx.RequestError as exc:
      logger.error(f"Error making request to OpenRouter: {exc}")
      return JSONResponse(
          status_code=500,
          content={"error": f"Error proxying request: {str(exc)}"}
      )

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