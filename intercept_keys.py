import secrets
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select
import logging
import httpx
import uuid
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import func

from database import get_db
from models import InterceptKey, OpenRouterGuestKey
from auth import get_current_user, UserInfo
import uuid
from config import settings
from provider_keys import GenerateGuestKeyResponseDto


logger = logging.getLogger(__name__)



class NewInterceptKeyResponse(BaseModel):
  intercept_key: str
  matching_openrouter_key: str
  message: str

class InterceptKeyDetails(BaseModel):
  intercept_key: str
  created_at: datetime
  is_valid: bool

  class Config:
    from_attributes = True

class ListInterceptKeysResponse(BaseModel):
  keys: List[InterceptKeyDetails]

router = APIRouter(
  prefix='/intercept-keys',
  tags=["Intercept keys"],
  dependencies=[Depends(get_current_user)]
)

@router.post('/',
             response_model=NewInterceptKeyResponse,
             status_code=status.HTTP_201_CREATED)
async def create_new_intercept_key(
  current_user: UserInfo = Depends(get_current_user),
  session: AsyncSession = Depends(get_db)
):

  new_key_value = secrets.token_urlsafe(32)

  new_intercept_key_db_row = InterceptKey(
    user_id=current_user.sub,
    intercept_key=new_key_value,
    is_valid=True
  )

  try:
    session.add(new_intercept_key_db_row)
    await session.commit()
  except Exception as e:
    await session.rollback()
    print(f"Error saving new intercept key: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="could not create intercept key row in db"
    )
  
  return NewInterceptKeyResponse(
    intercept_key=new_key_value,
    message="New intercept key created successfully"
  )

@router.post('/guest',
             response_model=NewInterceptKeyResponse,
             status_code=status.HTTP_201_CREATED)
async def create_new_intercept_key(
  session: AsyncSession = Depends(get_db)
):
  # validate it is a valid UUID
  guest_user_uuid = str(uuid.uuid4())

  new_key_value_token = secrets.token_urlsafe(40)
  new_key_value = str(uuid.uuid4())# f"sk-intercebd-v1-{new_key_value_token}"

  guest_user_id = f"guest_{guest_user_uuid}"

  try:
    openrouter_guest_key = await generate_guest_openrouter_api_key(session, user_id=guest_user_id)
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Failed to generate OpenRouter guest key, {e}"
    )

  new_intercept_key_db_row = InterceptKey(
    user_id=guest_user_id,
    intercept_key=new_key_value,
    is_valid=True
  )

  try:
    session.add(new_intercept_key_db_row)
    await session.commit()
  except Exception as e:
    await session.rollback()
    print(f"Error saving new intercept key: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="could not create intercept key row in db"
    )
  
  try:
    matching_openrouter_key = await find_openrouter_key_by_intercept_key(new_key_value, session)
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Failed to find OpenRouter key by intercept key, {e}"
    )

  return NewInterceptKeyResponse(
    intercept_key=new_key_value,
    matching_openrouter_key=matching_openrouter_key.or_key,
    message="New intercept key created successfully"
  )


@router.get('/', response_model=ListInterceptKeysResponse)
async def list_intercept_keys(
  current_user: UserInfo = Depends(get_current_user),
  session: AsyncSession = Depends(get_db)
):
  stmt = select(InterceptKey).where(InterceptKey.user_id == current_user.sub).order_by(InterceptKey.created_at.desc())
  results = await session.execute(stmt)
  user_keys = results.scalars().all()

  return ListInterceptKeysResponse(keys=user_keys)

async def generate_guest_openrouter_api_key(session : AsyncSession = Depends(get_db), user_id: str = None):
  openrouter_guest_api_key_uuid = str(uuid.uuid4())

  key_name = f"intercebd_guest_{openrouter_guest_api_key_uuid}"
  guest_limit = getattr(settings, "openrouter_provisioning_api_guest_limit", 5)
  try:
    async with httpx.AsyncClient() as client:
      response = await client.post(
        settings.openrouter_provisioning_api_base_url,
        headers = {
          "Authorization": f"Bearer {settings.openrouter_provisioning_api_key}",
          "Content-Type": "application/json"
        },
        json={
            "name": key_name,
            "label": "intercebd_guest",
            "limit": guest_limit,
        }
      )
      response.raise_for_status()
      response_data = response.json()
      logging.info(f"Successfully generated key via OpenRouter API: {response_data}")
  except httpx.RequestError as exc:
    logger.error(f"HTTP Request Error calling OpenRouter Provisioning API: {exc}")
    raise HTTPException(status_code=503, detail=f"Error communicating with OpenRouter API: {exc}")
  except httpx.HTTPStatusError as exc:
    logger.error(f"HTTP Status Error from OpenRouter Provisioning API: Status {exc.response.status_code}, Response: {exc.response.text}")
    raise HTTPException(status_code=exc.response.status_code, detail=f"OpenRouter API returned error: {exc.response.text}")
  except Exception as e:
    logger.error(f"Unexpected error during OpenRouter key generation: {e}")
    raise HTTPException(status_code=500, detail="Internal server error during key generation.")

  data_payload = response_data.get("data", {})
  key_value = response_data.get("key")

  if not data_payload or not key_value:
    logger.error(f"Incomplete response received from OpenRouter API: {response_data}")
    raise HTTPException(status_code=500, detail="Incomplete response received from OpenRouter API.")

  # Convert created_at string to datetime object safely
  created_at_api_str = data_payload.get("created_at")
  created_at_api_dt = None
  if created_at_api_str:
    try:
      # Handle potential timezone variations (e.g., Z or +00:00)
      if created_at_api_str.endswith('Z'):
        created_at_api_str = created_at_api_str[:-1] + '+00:00'
      created_at_api_dt = datetime.fromisoformat(created_at_api_str)
    except (ValueError, TypeError) as dt_err:
      logger.error(f"Could not parse created_at from OpenRouter response: {created_at_api_str}. Error: {dt_err}")
      raise HTTPException(status_code=500, detail="Could not parse timestamp from OpenRouter API response.")
  else:
    logger.warning("created_at field missing from OpenRouter API response.")
    raise HTTPException(status_code=500, detail="Timestamp missing from OpenRouter API response.")


  # Create new database record - Use correct column names from models.py
  new_key_record = OpenRouterGuestKey(
      or_key_hash=data_payload.get("hash"), # Changed from key_hash
      or_name=data_payload.get("name"),     # Changed from name
      or_label=data_payload.get("label"),   # Changed from label
      or_key=key_value,                     # Changed from key_value
      or_limit=data_payload.get("limit"),   # Changed from limit_usd (assuming limit is int as per model)
      or_usage=data_payload.get("usage", 0),# Changed from usage_usd (assuming usage is int as per model)
      or_created_at=created_at_api_dt,      # Changed from created_at_api
      is_active=not data_payload.get("disabled", False), # Keep is_active
      or_disabled=data_payload.get("disabled", False), # Add or_disabled
      user_id=user_id
  )

  try:
    session.add(new_key_record)
    await session.commit()
    await session.refresh(new_key_record) # Get DB-generated values
    logger.info(f"Successfully stored new OpenRouter guest key in DB with ID: {new_key_record.id}")
  except Exception as db_exc: # Catch potential database errors (e.g., unique constraint)
    logger.error(f"Database error saving new OpenRouter key: {db_exc}")
    await session.rollback()
    raise HTTPException(status_code=500, detail="Failed to save generated key to database.")

  try:
    response_dto = GenerateGuestKeyResponseDto.model_validate(new_key_record)
  except Exception as validation_exc:
    logger.error(f"Error validating response DTO from model: {validation_exc}")
    # Handle the case where the model data doesn't match the DTO schema
    raise HTTPException(status_code=500, detail="Internal server error creating response.")

  return response_dto

# ...existing code...
from sqlalchemy import select # Make sure select is imported
from typing import Optional # Import Optional for return type hint
from models import InterceptKey, OpenRouterGuestKey # Ensure models are imported

# ... other functions ...

async def find_openrouter_key_by_intercept_key(intercept_key_value: str, session: AsyncSession) -> Optional[OpenRouterGuestKey]:
    """
    Finds an OpenRouterGuestKey associated with a given InterceptKey.

    Args:
        intercept_key_value: The intercept key string to look up.
        session: The database session.

    Returns:
        The found OpenRouterGuestKey object, or None if not found or
        if the intercept key itself is not found.
    """
    logger.debug(f"Attempting to find intercept key: {intercept_key_value}")
    # 1. Find the InterceptKey record
    stmt_intercept = select(InterceptKey).where(InterceptKey.intercept_key == intercept_key_value)
    result_intercept = await session.execute(stmt_intercept)
    intercept_key_record = result_intercept.scalars().first()
    logger.debug(f"Intercept key record: {intercept_key_record}")
    if not intercept_key_record:
        logger.warning(f"Intercept key not found in database: {intercept_key_value}")
        return None

    if not intercept_key_record.user_id:
        logger.warning(f"Intercept key {intercept_key_value} found, but has no associated user_id.")
        return None

    logger.debug(f"Found intercept key record for user_id: {intercept_key_record.user_id}")

    # 2. Find the OpenRouterGuestKey using the user_id from the InterceptKey
    stmt_openrouter = select(OpenRouterGuestKey).where(OpenRouterGuestKey.user_id == intercept_key_record.user_id)
    result_openrouter = await session.execute(stmt_openrouter)
    logger.debug(f"OpenRouterGuestKey query result: {result_openrouter}")
    openrouter_key_record = result_openrouter.scalars().first()
    logger.debug(f"OpenRouterGuestKey record: {openrouter_key_record}")
    if not openrouter_key_record:
        logger.warning(f"No OpenRouterGuestKey found for user_id: {intercept_key_record.user_id} (associated with intercept key {intercept_key_value})")
        return None

    logger.info(f"Found OpenRouterGuestKey with ID {openrouter_key_record.id} for user_id: {intercept_key_record.user_id}")
    return openrouter_key_record

# ... rest of the file ...