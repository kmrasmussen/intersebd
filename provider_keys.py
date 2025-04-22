from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import uuid
from datetime import datetime
import logging
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

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
    or_updated_at: Optional[datetime] = None
    or_key: str
    or_usage: int
    is_active: bool
    user_id: Optional[uuid.UUID] = None
    completion_project_call_key_id: Optional[uuid.UUID] = None

    class Config:
      from_attributes = True

async def _fetch_new_openrouter_key_data() -> Dict[str, Any]:
    """
    Calls the OpenRouter provisioning API to generate a new guest key
    and returns the relevant data as a dictionary.
    Raises HTTPException on failure.
    """
    openrouter_guest_api_key_uuid = str(uuid.uuid4())
    key_name = f"intercebd_guest_{openrouter_guest_api_key_uuid}"
    guest_limit = getattr(settings, "openrouter_provisioning_api_guest_limit", 5)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.openrouter_provisioning_api_base_url,
                headers={
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
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Error communicating with key provider API: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP Status Error from OpenRouter Provisioning API: Status {exc.response.status_code}, Response: {exc.response.text}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Key provider API returned error: {exc.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error during OpenRouter key generation call: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during key generation.")

    data_payload = response_data.get("data", {})
    key_value = response_data.get("key")

    if not data_payload or not key_value:
        logger.error(f"Incomplete response received from OpenRouter API: {response_data}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Incomplete response received from key provider API.")

    created_at_api_str = data_payload.get("created_at")
    created_at_api_dt = None
    if created_at_api_str:
        try:
            if created_at_api_str.endswith('Z'):
                created_at_api_str = created_at_api_str[:-1] + '+00:00'
            created_at_api_dt = datetime.fromisoformat(created_at_api_str)
        except (ValueError, TypeError) as dt_err:
            logger.error(f"Could not parse created_at from OpenRouter response: {created_at_api_str}. Error: {dt_err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not parse timestamp from key provider API response.")
    else:
        logger.warning("created_at field missing from OpenRouter API response.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Timestamp missing from key provider API response.")

    return {
        "or_key_hash": data_payload.get("hash"),
        "or_name": data_payload.get("name"),
        "or_label": data_payload.get("label"),
        "or_key": key_value,
        "or_limit": data_payload.get("limit"),
        "or_usage": data_payload.get("usage", 0),
        "or_created_at": created_at_api_dt,
        "is_active": not data_payload.get("disabled", False),
        "or_disabled": data_payload.get("disabled", False)
    }