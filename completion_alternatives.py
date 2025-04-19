import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging
from datetime import datetime
from typing import List

from database import get_db
from models import CompletionAlternative, CompletionsRequest, AnnotationTarget

logger = logging.getLogger(__name__)

router = APIRouter(
  prefix="/completion-alternatives",
  tags=["Completion Alternatives"]
)

class AlternativeCompletionRequest(BaseModel):
    intercept_key: str
    completion_request_id: uuid.UUID
    alternative_content: str
    rater_id: str | None = None # Optional rater ID

class AlternativeCompletionResponse(BaseModel):
    alternative_id: uuid.UUID
    message: str

@router.post(
    "/",
    response_model=AlternativeCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alternative_completion(
    request: AlternativeCompletionRequest,
    session: AsyncSession = Depends(get_db),
):
  logger.info(f"Received request to add alternative for completion request ID: {request.completion_request_id}")

  try:
    stmt = select(CompletionsRequest).where(CompletionsRequest.id == request.completion_request_id)
    result = await session.execute(stmt)
    original_request = result.scalar_one_or_none()

    if not original_request:
      logger.warning(f"Original completion request with ID {request.completion_request_id} not found.")
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Original completion request not found."
      )
    
    if original_request.intercept_key != request.intercept_key:
      logger.warning(f"Intercept key mismatch for completion request ID {request.completion_request_id}.")
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Intercept key does not match the original request."
      )
    
    new_annotation_target = AnnotationTarget()
    session.add(new_annotation_target)
    await session.flush()
    logger.info(f'Created annotation target with id {new_annotation_target.id} for alternative')

    new_alternative = CompletionAlternative(
      original_completion_request_id=request.completion_request_id,
      intercept_key=request.intercept_key,
      alternative_content=request.alternative_content,
      rater_id=request.rater_id,
      annotation_target_id=new_annotation_target.id
    )
    session.add(new_alternative)
    await session.commit()
    await session.refresh(new_alternative)

    logger.info(f"Successfully created alternative completion with id {new_alternative.id} for request ID {request.completion_request_id}.")
    return AlternativeCompletionResponse(
        alternative_id=new_alternative.id,
        message="Alternative completion created successfully."
    )
  except HTTPException as e:
    logger.error(f"HTTPException: {e.detail}")
    await session.rollback()
    raise e
  except Exception as e:
    await session.rollback()
    logger.exception(f"Unexpected error: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred when creating the alternative completion."
    )
  
class CompletionAlternativeItem(BaseModel):
    id: uuid.UUID
    alternative_content: str
    rater_id: str | None
    created_at: datetime
    annotation_target_id: uuid.UUID # <--- ADD THIS FIELD

    class Config:
      from_attributes = True # Enable ORM mode for easy conversion from SQLAlchemy model


class ListAlternativesRequest(BaseModel):
    completion_request_id: uuid.UUID
    intercept_key: str

class ListAlternativesResponse(BaseModel):
    alternatives: List[CompletionAlternativeItem]

@router.post( # Changed from GET to POST
    "/list-by-request", # Changed path, removed path parameter
    response_model=ListAlternativesResponse,
    status_code=status.HTTP_200_OK,
)
async def list_alternatives_for_request(
    request_data: ListAlternativesRequest, # Use the new request body model
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieves all alternative completions submitted for a specific
    original completion request ID, validating the provided intercept key.
    """
    logger.info(f"Fetching alternatives for completion request ID: {request_data.completion_request_id}")

    try:
        # 1. Find the original completion request to validate the key
        stmt_validate = select(CompletionsRequest).where(CompletionsRequest.id == request_data.completion_request_id)
        result_validate = await session.execute(stmt_validate)
        original_request = result_validate.scalar_one_or_none()

        if not original_request:
            logger.warning(f"Original completion request not found for validation: {request_data.completion_request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original completion request not found."
            )

        # 2. Validate the intercept key
        if original_request.intercept_key != request_data.intercept_key:
            logger.warning(f"Intercept key mismatch when listing alternatives for request {request_data.completion_request_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, # Use 403 Forbidden for auth failure
                detail="Provided intercept key does not match the original request."
            )

        # 3. Query for alternatives matching the request ID (Validation passed)
        stmt_list = select(CompletionAlternative).where(
            CompletionAlternative.original_completion_request_id == request_data.completion_request_id
        ).order_by(CompletionAlternative.created_at)

        result_list = await session.execute(stmt_list)
        alternatives_db = result_list.scalars().all()

        if not alternatives_db:
            logger.info(f"No alternatives found for request ID: {request_data.completion_request_id}")
            return ListAlternativesResponse(alternatives=[])

        logger.info(f"Found {len(alternatives_db)} alternatives for request ID: {request_data.completion_request_id}")
        # Pydantic automatically maps annotation_target_id due to from_attributes=True
        return ListAlternativesResponse(alternatives=alternatives_db)

    except HTTPException as http_exc:
        # Re-raise specific HTTP exceptions
        await session.rollback()
        raise http_exc
    except Exception as e:
        await session.rollback()
        logger.exception(f"Error fetching alternatives for request ID {request_data.completion_request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching alternatives."
        )