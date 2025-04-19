import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field # Import BaseModel and Field
from datetime import datetime # Import datetime

from database import get_db
from models import CompletionsRequest, CompletionResponse, RequestsLog, InterceptKey # Import necessary models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/completion-pairs",
    tags=["Completion Pairs"]
)

class CompletionsRequestDetailDto(BaseModel):
    id: uuid.UUID
    request_log_id: uuid.UUID
    intercept_key: str
    messages: Optional[Any] = None # Or specify a more detailed model if needed
    model: Optional[str] = None
    response_format: Optional[Any] = None # Or specify a more detailed model
    request_timestamp: Optional[datetime] = None # Added field

    class Config:
        from_attributes = True # Enable ORM mode

class CompletionResponseDetailDto(BaseModel):
    id: str # This is the OpenAI/Provider ID, which is a string
    completion_request_id: uuid.UUID
    annotation_target_id: Optional[uuid.UUID] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    created: Optional[int] = None # Unix timestamp
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    choice_finish_reason: Optional[str] = None
    choice_role: Optional[str] = None
    choice_content: Optional[str] = None

    class Config:
        from_attributes = True # Enable ORM mode

class CompletionPairDto(BaseModel):
    request: CompletionsRequestDetailDto
    response: Optional[CompletionResponseDetailDto] = None

    class Config:
        from_attributes = True

class CompletionPairListResponseDto(BaseModel):
    pairs: List[CompletionPairDto]
    intercept_key: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/view/{viewing_id}", response_model=CompletionPairListResponseDto)
async def list_completion_pairs( # Renamed function in previous step, ensure consistency
    viewing_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of completion request and response pairs
    associated with a specific intercept key (found via viewing_id),
    and includes the intercept key in the response.
    """
    logger.info(f"Fetching completion pairs for viewing_id: {viewing_id}")
    intercept_key_to_return = None # Variable to hold the key
    try:
        # Find the corresponding intercept_key first
        key_lookup_stmt = select(InterceptKey.intercept_key).where(InterceptKey.viewing_id == viewing_id)
        key_result = await session.execute(key_lookup_stmt)
        intercept_key = key_result.scalar_one_or_none()
        intercept_key_to_return = intercept_key # Store the key to return it later

        if not intercept_key:
            logger.warning(f"No intercept key found for viewing ID: {viewing_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewing ID not found.")

        # Proceed to fetch pairs using the found intercept_key
        stmt = (
            select(CompletionsRequest, CompletionResponse, RequestsLog.log_timestamp)
            .outerjoin(CompletionResponse, CompletionsRequest.id == CompletionResponse.completion_request_id)
            .join(RequestsLog, CompletionsRequest.request_log_id == RequestsLog.id)
            .where(CompletionsRequest.intercept_key == intercept_key)
            .order_by(RequestsLog.log_timestamp.desc())
        )

        result = await session.execute(stmt)
        db_pairs = result.unique().all()

        # If no pairs found, return empty list BUT include the intercept_key
        if not db_pairs:
            logger.warning(f"No completion pairs found for intercept key: {intercept_key} (viewing ID: {viewing_id})")
            # Return the DTO with the key and empty pairs list
            return CompletionPairListResponseDto(pairs=[], intercept_key=intercept_key_to_return)

        # Map database results to DTOs if pairs exist
        response_pairs = []
        for req, resp, timestamp in db_pairs:
            request_dto_data = req.__dict__
            request_dto_data['request_timestamp'] = timestamp
            request_dto = CompletionsRequestDetailDto.model_validate(request_dto_data)

            response_dto = None
            if resp:
                response_dto = CompletionResponseDetailDto.model_validate(resp)

            response_pairs.append(CompletionPairDto(request=request_dto, response=response_dto))

        logger.info(f"Successfully retrieved {len(response_pairs)} pairs for intercept key: {intercept_key}")
        # Return the DTO with the key and the populated pairs list
        return CompletionPairListResponseDto(pairs=response_pairs, intercept_key=intercept_key_to_return)

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        # Log the intercept_key if available during generic error
        log_key = intercept_key_to_return or "unknown (lookup failed)"
        logger.exception(f"Error retrieving completion pairs for viewing ID {viewing_id} (Intercept Key: {log_key}): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while retrieving completion pairs.")
