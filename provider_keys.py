from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import uuid
from datetime import datetime
import logging
from pydantic import BaseModel
from typing import List, Optional

from database import get_db
from models import OpenRouterGuestKey
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
  prefix="/provider-keys",
  tags=["Provider keys"],
)

class GenerateGuestKeyResponseDto(BaseModel):
    id: uuid.UUID
    or_key_hash : str
    or_name: str
    or_label: str
    or_disabled: bool
    or_limit: int
    or_created_at: datetime
    or_created_at: datetime
    or_updated_at: datetime
    or_key: str
    or_usage: int
    is_active: bool
    user_id: Optional[str] = None

    class Config:
      from_attributes = True

@router.post('/openrouter/generate_guest_api_key', response_model=GenerateGuestKeyResponseDto)
async def generate_guest_openrouter_api_key(session : AsyncSession = Depends(get_db)):
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
      or_disabled=data_payload.get("disabled", False) # Add or_disabled
      # or_updated_at will be handled by the DB default/onupdate
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