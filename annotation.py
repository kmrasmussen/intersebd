from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, Field # Import BaseModel and Field
from datetime import datetime

# Assuming models and get_db are accessible
from models import CompletionResponse, CompletionAnnotation, AnnotationTarget, InterceptKey, CompletionsRequest
from database import get_db

import logging

logger = logging.getLogger(__name__)
# --- Pydantic Schemas ---

class AnnotationResponseSchema(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    rater_id: Optional[str] = None
    reward: Optional[float] = None
    annotation_metadata: Optional[Dict[str, Any]] = None

    class Config:
      from_attributes = True

class GetAnnotationsSchema(BaseModel):
    completion_response_id: str
    intercept_key: str

class AnnotationCreateSchema(BaseModel):
    annotation_target_id: uuid.UUID
    intercept_key: str # Key to verify ownership/permission
    rater_id: Optional[str] = None
    reward: Optional[float] = None
    annotation_metadata: Optional[Dict[str, Any]] = None

# ... (imports and schemas from above) ...

# --- Router Definition ---
router = APIRouter(
    prefix="/annotations",
    tags=["annotations"],
)

# --- Endpoint Implementation ---

@router.post( # Changed from GET to POST
    "/completion-response/list", # Changed path, removed ID from path
    response_model=List[AnnotationResponseSchema],
    summary="Get annotations for a specific completion response (using POST for key security)"
)
async def get_annotations_for_completion_response_post( # Renamed function slightly
    request_data: GetAnnotationsSchema, # Accept data from request body
    session: AsyncSession = Depends(get_db)
):
    completion_response_id = request_data.completion_response_id
    intercept_key = request_data.intercept_key
    """
    Retrieves all annotations associated with a given CompletionResponse ID,
    verifying ownership via the intercept key.
    """
    # Query for the CompletionResponse, eagerly loading the target and its annotations
    stmt = (
        select(CompletionResponse)
        .where(CompletionResponse.id == completion_response_id)
        .options(
            selectinload(CompletionResponse.annotation_target) # Load the target
            .selectinload(AnnotationTarget.annotations) # Load annotations from the target
        )
        .options(
            selectinload(CompletionResponse.completion_request) # Load request to check intercept key
            .selectinload(CompletionsRequest.key_info)
        )
    )
    result = await session.execute(stmt)
    response = result.scalar_one_or_none()

    if not response:
        raise HTTPException(status_code=404, detail="CompletionResponse not found")

    # Verify intercept key matches the one associated with the request
    if not response.completion_request or not response.completion_request.key_info or response.completion_request.intercept_key != intercept_key:
         raise HTTPException(status_code=403, detail="Intercept key does not match the completion response or access denied")

    # Check if the annotation target exists (should always exist due to non-nullable FK)
    if not response.annotation_target:
        # This case should ideally not happen if data integrity is maintained
        raise HTTPException(status_code=404, detail="AnnotationTarget not found for this CompletionResponse")

    # Return the list of annotations from the target
    # Pydantic will automatically convert CompletionAnnotation objects
    # to AnnotationResponseSchema thanks to orm_mode=True
    return response.annotation_target.annotations
# ... (imports, schemas, router setup) ...

# --- Endpoint Implementation ---

# ... (existing GET endpoint) ...

@router.post(
    "/",
    response_model=AnnotationResponseSchema,
    status_code=status.HTTP_201_CREATED, # Use 201 for successful creation
    summary="Create an annotation for a target"
)
async def create_annotation(
    annotation_data: AnnotationCreateSchema,
    session: AsyncSession = Depends(get_db)
):
    """
    Creates a new annotation and links it to the specified AnnotationTarget,
    verifying ownership via the intercept key associated with the original request
    or alternative.
    """
    # 1. Find the AnnotationTarget, loading related objects needed for verification
    stmt = (
        select(AnnotationTarget)
        .where(AnnotationTarget.id == annotation_data.annotation_target_id)
        .options(
            # Load the response and its request for key check
            selectinload(AnnotationTarget.completion_response)
            .selectinload(CompletionResponse.completion_request),
            # Load the alternative for key check
            selectinload(AnnotationTarget.completion_alternative)
        )
    )
    result = await session.execute(stmt)
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AnnotationTarget not found"
        )

    # 2. Determine the associated intercept key and verify
    associated_intercept_key: Optional[str] = None
    if target.completion_response and target.completion_response.completion_request:
        associated_intercept_key = target.completion_response.completion_request.intercept_key
    elif target.completion_alternative:
        associated_intercept_key = target.completion_alternative.intercept_key
    else:
        # This should not happen if data integrity is maintained
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AnnotationTarget is not linked to a known source (Response or Alternative)"
        )

    if associated_intercept_key != annotation_data.intercept_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provided intercept key does not match the target's associated key or access denied"
        )

    # 3. Create the new annotation
    new_annotation = CompletionAnnotation(
        rater_id=annotation_data.rater_id,
        reward=annotation_data.reward,
        annotation_metadata=annotation_data.annotation_metadata
        # timestamp is handled by server_default
    )

    # 4. Link the annotation to the target (for many-to-many)
    new_annotation.annotation_targets.append(target)

    # 5. Add to session and commit
    session.add(new_annotation)
    try:
        await session.commit()
        await session.refresh(new_annotation) # Refresh to load default values like timestamp
    except Exception as e:
        await session.rollback()
        # Log the exception e
        logger.error(f"Error creating annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save annotation to database"
        )

    # 6. Return the created annotation data
    return new_annotation
