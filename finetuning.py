from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Set
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import and_
import logging

# Assuming get_db and models are accessible (adjust imports as needed)
from database import get_db
import models
from security import get_intercept_key_from_header

logger = logging.getLogger(__name__)

# --- Pydantic Schemas ---

class SftMessageSchema(BaseModel):
    """Represents a single message turn in a conversation."""
    role: str = Field(..., description="Role of the speaker (e.g., 'system', 'user', 'assistant')")
    content: str = Field(..., description="The text content of the message")
    weight: Optional[int] = Field(None, description="Weight for fine-tuning (0 or 1, default is None/ignored)")

    class Config:
        orm_mode = False # Not directly mapping from ORM for this structure

class SftConversationSchema(BaseModel):
    """Represents a full conversation, typically a list of messages."""
    messages: List[SftMessageSchema] = Field(..., description="A list of messages forming the conversation")

    class Config:
        orm_mode = False # Not directly mapping from ORM for this structure

# --- Router Setup ---

router = APIRouter(
    prefix="/finetuning",
    tags=["Finetuning"],
    responses={
        404: {"description": "Not found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)

# --- Endpoint Definition ---

@router.post(
    "/sftdataset",
    response_model=List[SftConversationSchema],
    summary="Generate an SFT dataset from annotated conversations",
    response_model_exclude_none=True  # <-- ADD THIS LINE
)
async def generate_sft_dataset(
    intercept_key: str = Depends(get_intercept_key_from_header),
    session: AsyncSession = Depends(get_db)
):
    """
    Generates a dataset suitable for Supervised Fine-Tuning (SFT).

    It retrieves conversation histories (requests) associated with the provided
    intercept key (from Authorization header) and formats them based on
    positively annotated (reward=1) responses or alternatives.
    """
    logger.info(f"Generating SFT dataset for intercept key (last 4): ...{intercept_key[-4:]}")
    sft_dataset: List[SftConversationSchema] = []
    potential_target_ids: Set[uuid.UUID] = set()

    # 1. Query 1: Fetch relevant requests + eager load responses/alternatives + targets
    logger.debug("Executing Query 1: Fetching requests and candidates...")
    stmt_requests = (
        select(models.CompletionsRequest)
        .where(models.CompletionsRequest.intercept_key == intercept_key)
        .options(
            selectinload(models.CompletionsRequest.completion_response)
            .selectinload(models.CompletionResponse.annotation_target),
            selectinload(models.CompletionsRequest.alternatives)
            .selectinload(models.CompletionAlternative.annotation_target)
        )
        .order_by(models.CompletionsRequest.id)
    )
    result_requests = await session.execute(stmt_requests)
    requests_with_candidates = result_requests.scalars().unique().all()
    logger.debug(f"Found {len(requests_with_candidates)} requests for key.")

    # 2. Collect potential target IDs
    logger.debug("Collecting potential annotation target IDs...")
    for req in requests_with_candidates:
        if req.completion_response and req.completion_response.annotation_target:
            potential_target_ids.add(req.completion_response.annotation_target.id)
        for alt in req.alternatives:
            if alt.annotation_target:
                potential_target_ids.add(alt.annotation_target.id)

    if not potential_target_ids:
        logger.info("No potential annotation targets found for this key. Returning empty dataset.")
        return []
    logger.debug(f"Collected {len(potential_target_ids)} potential target IDs.")

    # 3. Query 2: Identify positively annotated targets (reward=1)
    logger.debug("Executing Query 2: Identifying positively annotated targets...")
    stmt_valid_targets = (
        select(models.AnnotationTarget.id)
        .distinct()
        .join(models.annotation_target_annotation_link)
        .join(models.CompletionAnnotation)
        .where(
            and_(
                models.AnnotationTarget.id.in_(potential_target_ids),
                models.CompletionAnnotation.reward == 1
            )
        )
    )
    result_valid_targets = await session.execute(stmt_valid_targets)
    valid_target_ids: Set[uuid.UUID] = set(result_valid_targets.scalars().all())
    logger.debug(f"Found {len(valid_target_ids)} positively annotated targets.")

    if not valid_target_ids:
        logger.info("None of the potential targets have positive (reward=1) annotations. Returning empty dataset.")
        return []

    # 4. Python Processing: Iterate, check annotations, format conversations
    logger.debug("Processing requests and formatting SFT dataset...")
    for req in requests_with_candidates:
        base_messages_data = req.messages
        if not isinstance(base_messages_data, list):
             logger.warning(f"Request {req.id} messages field is not a list, skipping.")
             continue

        try:
            # Ensure weight is None unless explicitly set (like for assistant)
            base_messages = [
                SftMessageSchema(
                    role=msg.get("role"),
                    content=msg.get("content"),
                    weight=None # Explicitly set to None here
                )
                for msg in base_messages_data
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg
            ]
        except Exception as e:
            logger.warning(f"Failed to parse messages for request {req.id}: {e}, skipping.")
            continue

        if (req.completion_response and
            req.completion_response.annotation_target and
            req.completion_response.annotation_target.id in valid_target_ids):
            assistant_message = SftMessageSchema(
                role="assistant",
                content=req.completion_response.choice_content or "",
                weight=None
            )
            conversation = SftConversationSchema(messages=base_messages + [assistant_message])
            sft_dataset.append(conversation)
            logger.debug(f"Added SFT entry from request {req.id} - original response")

        for alt in req.alternatives:
            if (alt.annotation_target and
                alt.annotation_target.id in valid_target_ids):
                assistant_message = SftMessageSchema(
                    role="assistant",
                    content=alt.alternative_content or "",
                    weight=None
                )
                conversation = SftConversationSchema(messages=base_messages + [assistant_message])
                sft_dataset.append(conversation)
                logger.debug(f"Added SFT entry from request {req.id} - alternative {alt.id}")

    logger.info(f"Generated {len(sft_dataset)} SFT conversation entries.")
    return sft_dataset
