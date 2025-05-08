from fastapi import APIRouter, Path, HTTPException, Depends, status, Body, Query

from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any, Union
import uuid
import logging
import json
from datetime import datetime, timezone
import huggingface_hub
import datasets
from datasets import Dataset
import uuid
from fastapi import Query

# --- DB and Auth Imports ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload, aliased, contains_eager
from sqlalchemy.exc import IntegrityError  # Import IntegrityError
from database import get_db
from auth import verify_project_membership, get_current_user
import models
from models import User
from jsonschema import validate as validate_jsonschema  # Import the validator function
from jsonschema import Draft7Validator  # Import the specific validator class
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError  # Import the specific exception
from fastapi import Response

logger = logging.getLogger(__name__)

# --- Define Data Structures ---
RequestStatus = Literal["complete", "partial", "none"]

class MockRequestSummary(BaseModel):
    id: str
    name: str
    question: str
    totalResponses: int
    annotatedResponses: int
    timestamp: str
    sftStatus: RequestStatus
    dpoStatus: RequestStatus

class Message(BaseModel):
    role: str
    content: str

class Annotation(BaseModel):
    id: str
    reward: int
    by: str
    at: str

class ResponseDetail(BaseModel):
    id: str
    annotation_target_id: Optional[str] = None
    content: str
    model: str
    created: str
    annotations: List[Annotation]
    metadata: Optional[Dict[str, Any]] = None
    is_json: bool
    obeys_schema: Optional[bool] = None

class RequestDetailData(BaseModel):
    id: str
    project_id: str
    messages: List[Message]
    model: str
    response_format: Optional[Dict[str, Any]] = None
    request_timestamp: str

class MockRequestDetail(BaseModel):
    id: str
    name: str
    pairNumber: int
    request: RequestDetailData
    mainResponse: ResponseDetail
    alternativeResponses: List[ResponseDetail]

# --- NEW: Annotation Request/Response Models ---
class CreateAnnotationRequest(BaseModel):
    reward: float
    annotation_metadata: Optional[Dict[str, Any]] = None

class AnnotationResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user_id: Optional[uuid.UUID]
    reward: float
    annotation_metadata: Optional[Dict[str, Any]]
    annotation_target_id: uuid.UUID

    class Config:
        from_attributes = True

class CreateAlternativeRequest(BaseModel):
    alternative_content: str = Field(..., description="The content of the alternative response.")

class CreateAlternativeResponse(ResponseDetail):
    pass

class JsonSchemaContent(BaseModel):
    schema_content: Dict[str, Any] = Field(..., description="The JSON schema content.")

class ProjectJsonSchemaResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    schema_content: Dict[str, Any]
    created_at: datetime
    is_active: bool  # Will always be true when setting as current

    class Config:
        from_attributes = True

class SftRequestCountResponse(BaseModel):
    sft_request_count: int

class DpoReadyCountResponse(BaseModel):
    dpo_ready_count: int

# --- NEW: Schemas for SFT Dataset Generation ---
class SftMessageSchema(BaseModel):
    """Represents a single message turn in a conversation."""
    role: str = Field(..., description="Role of the speaker (e.g., 'system', 'user', 'assistant')")
    content: str = Field(..., description="The text content of the message")

    class Config:
        from_attributes = True

class SftConversationSchema(BaseModel):
    """Represents a full conversation, typically a list of messages."""
    messages: List[SftMessageSchema] = Field(..., description="A list of messages forming the conversation")
    class Config:
        from_attributes = True

class DpoInputSchema(BaseModel):
    messages: List[SftMessageSchema] # Reusing SftMessageSchema for input messages
    tools: List[Any] = Field(default_factory=list, description="List of tools, if any.")
    parallel_tool_calls: bool = Field(True, description="Whether parallel tool calls are enabled.")

class DpoAssistantMessageSchema(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str

    class Config:
        from_attributes = True

class DpoExampleSchema(BaseModel):
    input: DpoInputSchema
    preferred_output: List[DpoAssistantMessageSchema]
    non_preferred_output: List[DpoAssistantMessageSchema]

    class Config:
        from_attributes = True

# --- End NEW Schemas ---

# --- Helper Functions ---

def format_timestamp(ts: Optional[Union[int, datetime]]) -> str:
    """Converts Unix timestamp (int) or datetime object to ISO 8601 string."""
    if ts is None:
        return "N/A"
    try:
        if isinstance(ts, int):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(ts, datetime):
            if ts.tzinfo is None:
                dt = ts.replace(tzinfo=timezone.utc)
            else:
                dt = ts.astimezone(timezone.utc)
        else:
            logger.warning(f"Invalid type for timestamp formatting: {type(ts)}")
            return "N/A"
        return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    except (ValueError, TypeError, OverflowError) as e:
        logger.warning(f"Could not format timestamp {ts}: {e}")
        return "N/A"

def check_json(content: Optional[str]) -> bool:
    """Checks if a string is valid JSON."""
    if not content:
        return False
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        return False

def map_annotations(db_annotations: Optional[List[models.CompletionAnnotation]]) -> List[Annotation]:
    """Maps database annotation objects to Pydantic Annotation models."""
    if not db_annotations:
        return []
    mapped = []
    for ann in db_annotations:
        try:
            # Keep reward conversion as is (DB Float -> Pydantic int)
            reward_int = int(ann.reward) if ann.reward is not None else 0
        except (ValueError, TypeError):
            reward_int = 0 # Default to 0 if conversion fails

        annotator_str = "Unknown"
        if ann.user_id:
            annotator_str = str(ann.user_id)

        mapped.append(Annotation(
            id=str(ann.id),
            reward=reward_int,
            by=annotator_str,
            at=format_timestamp(ann.timestamp)
        ))
    return mapped

def map_to_response_detail(
    response_obj: Union[models.CompletionResponse, models.CompletionAlternative],
    request_model: str,
    active_schema: Optional[Dict[str, Any]] = None
) -> ResponseDetail:
    """Maps CompletionResponse or CompletionAlternative to Pydantic ResponseDetail,
       performing JSON and schema validation if an active schema is provided."""
    content = None
    created_ts = None
    db_annotations = None
    response_id = None
    annotation_target_id_str: Optional[str] = None

    if isinstance(response_obj, models.CompletionResponse):
        response_id = str(response_obj.id)
        content = response_obj.choice_content
        created_ts = response_obj.created
        if response_obj.annotation_target:
            db_annotations = response_obj.annotation_target.annotations
            annotation_target_id_str = str(response_obj.annotation_target.id)
        else:
            logger.warning(f"CompletionResponse {response_id} missing annotation_target link.")
    elif isinstance(response_obj, models.CompletionAlternative):
        response_id = str(response_obj.id)
        content = response_obj.alternative_content
        created_ts = response_obj.created_at
        if response_obj.annotation_target:
            db_annotations = response_obj.annotation_target.annotations
            annotation_target_id_str = str(response_obj.annotation_target.id)
        else:
            logger.warning(f"CompletionAlternative {response_id} missing annotation_target link.")
    else:
        logger.error(f"Invalid object type passed to map_to_response_detail: {type(response_obj)}")
        raise TypeError("Invalid object type for mapping to ResponseDetail")

    is_json = check_json(content)
    obeys_schema: Optional[bool] = None

    if is_json and active_schema and content:
        try:
            parsed_content = json.loads(content)
            validate_jsonschema(instance=parsed_content, schema=active_schema)
            obeys_schema = True
            logger.debug(f"Response content for {response_id} validated successfully against active schema.")
        except json.JSONDecodeError as json_err:
            logger.warning(f"JSONDecodeError during schema validation for {response_id} despite check_json passing: {json_err}")
            obeys_schema = False
        except JsonSchemaValidationError as schema_err:
            logger.debug(f"Response content for {response_id} failed schema validation: {schema_err.message}")
            obeys_schema = False
        except Exception as val_err:
            logger.error(f"Unexpected error during schema validation for {response_id}: {val_err}", exc_info=True)
            obeys_schema = False

    return ResponseDetail(
        id=response_id or "N/A",
        annotation_target_id=annotation_target_id_str,
        content=content or "",
        model=request_model,
        created=format_timestamp(created_ts),
        annotations=map_annotations(db_annotations),
        metadata=None,
        is_json=is_json,
        obeys_schema=obeys_schema
    )

async def _generate_project_sft_data(
    project_id: uuid.UUID,
    db: AsyncSession,
    sft_threshold: float = 0.75
) -> List[SftConversationSchema]:
    """
    Generates a list of SFT conversation data for a given project,
    based on the is_sft_example criteria.
    """
    logger.info(f"Generating SFT conversation data for project {project_id}")
    sft_dataset: List[SftConversationSchema] = []

    # --- Fetch Active Schema Once ---
    active_schema_content: Optional[Dict[str, Any]] = None
    try:
        stmt_schema = (
            select(models.ProjectJsonSchema)
            .where(models.ProjectJsonSchema.project_id == project_id)
            .where(models.ProjectJsonSchema.is_active == True)
            .order_by(models.ProjectJsonSchema.created_at.desc())
        )
        result_schema = await db.execute(stmt_schema)
        active_schema_obj = result_schema.scalars().first()
        if active_schema_obj:
            active_schema_content = active_schema_obj.schema_content
            logger.debug(f"Found active schema {active_schema_obj.id} for SFT dataset generation.")
        else:
            logger.debug(f"No active schema found for project {project_id}. SFT checks will only use reward.")
    except Exception as schema_exc:
        logger.error(f"Error fetching active schema for SFT dataset (project {project_id}): {schema_exc}", exc_info=True)
        # Proceed without schema validation if fetching fails
    # --- End Fetch Active Schema ---

    # --- Query to fetch requests and necessary related data ---
    # Same query structure as get_sft_request_count
    stmt_requests = (
        select(models.CompletionsRequest)
        .where(models.CompletionsRequest.project_id == project_id)
        .options(
            selectinload(models.CompletionsRequest.completion_response)
            .selectinload(models.CompletionResponse.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            ),
            selectinload(models.CompletionsRequest.alternatives)
            .selectinload(models.CompletionAlternative.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            )
        )
        .order_by(models.CompletionsRequest.id) # Consistent ordering is good practice
    )
    # --- End Query ---

    result = await db.execute(stmt_requests)
    requests = result.scalars().unique().all()
    logger.debug(f"Fetched {len(requests)} requests for SFT dataset generation.")

    # --- Process Requests and Build Dataset ---
    for req in requests:
        # 1. Parse Base Messages
        req_id_str = str(req.id)
        base_messages_data = req.messages
        if not isinstance(base_messages_data, list):
             logger.warning(f"Request {req.id} messages field is not a list, skipping for SFT.")
             continue
        try:
            base_messages = [
                SftMessageSchema(role=msg.get("role"), content=msg.get("content"))
                for msg in base_messages_data
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg
            ]
        except Exception as e:
            logger.warning(f"Failed to parse base messages for request {req.id}: {e}, skipping for SFT.")
            continue

        # 2. Check Main Response
        if req.completion_response and req.completion_response.annotation_target:
            target = req.completion_response.annotation_target
            if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                assistant_content = req.completion_response.choice_content or ""
                assistant_message = SftMessageSchema(role="assistant", content=assistant_content)
                conversation = SftConversationSchema(
                    messages=base_messages + [assistant_message])
                sft_dataset.append(conversation)
                logger.debug(f"Added SFT entry from request {req.id} - main response {req.completion_response.id}")

        # 3. Check Alternatives
        for alt in req.alternatives:
            if alt.annotation_target:
                target = alt.annotation_target
                if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                    assistant_content = alt.alternative_content or ""
                    assistant_message = SftMessageSchema(role="assistant", content=assistant_content)
                    conversation = SftConversationSchema(messages=base_messages + [assistant_message])
                    sft_dataset.append(conversation)
                    logger.debug(f"Added SFT entry from request {req.id} - alternative {alt.id}")

    logger.info(f"Generated {len(sft_dataset)} SFT conversation entries for project {project_id}.")
    return sft_dataset

async def _generate_project_dpo_data(
    project_id: uuid.UUID,
    db: AsyncSession,
    sft_threshold: float,
    dpo_negative_threshold: float
) -> List[DpoExampleSchema]:
    """
    Generates a list of DPO example data for a given project.
    Each example consists of an input, a preferred response (SFT),
    and a non-preferred response (DPO negative).
    """
    logger.info(f"Generating DPO dataset for project {project_id} with SFT threshold {sft_threshold} and DPO negative threshold {dpo_negative_threshold}")
    dpo_dataset: List[DpoExampleSchema] = []

    # --- Fetch Active Schema Once ---
    active_schema_content: Optional[Dict[str, Any]] = None
    try:
        stmt_schema = (
            select(models.ProjectJsonSchema)
            .where(models.ProjectJsonSchema.project_id == project_id)
            .where(models.ProjectJsonSchema.is_active == True)
            .order_by(models.ProjectJsonSchema.created_at.desc())
        )
        result_schema = await db.execute(stmt_schema)
        active_schema_obj = result_schema.scalars().first()
        if active_schema_obj:
            active_schema_content = active_schema_obj.schema_content
            logger.debug(f"Found active schema {active_schema_obj.id} for DPO dataset generation.")
        else:
            logger.debug(f"No active schema found for project {project_id}. DPO checks will only use reward.")
    except Exception as schema_exc:
        logger.error(f"Error fetching active schema for DPO dataset (project {project_id}): {schema_exc}", exc_info=True)
    # --- End Fetch Active Schema ---

    # --- Query to fetch requests and necessary related data ---
    stmt_requests = (
        select(models.CompletionsRequest)
        .where(models.CompletionsRequest.project_id == project_id)
        .options(
            selectinload(models.CompletionsRequest.completion_response)
            .selectinload(models.CompletionResponse.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            ),
            selectinload(models.CompletionsRequest.alternatives)
            .selectinload(models.CompletionAlternative.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            )
        )
        .order_by(models.CompletionsRequest.id) # Consistent ordering
    )
    # --- End Query ---

    result = await db.execute(stmt_requests)
    requests = result.scalars().unique().all()
    logger.debug(f"Fetched {len(requests)} requests for DPO dataset generation.")

    for req in requests:
        req_id_str = str(req.id)
        # Store tuples of (AnnotationTarget, content_string)
        sft_targets_with_content: List[tuple[models.AnnotationTarget, str]] = []
        dpo_negative_targets_with_content: List[tuple[models.AnnotationTarget, str]] = []

        all_targets_to_process: List[models.AnnotationTarget] = []
        if req.completion_response and req.completion_response.annotation_target:
            all_targets_to_process.append(req.completion_response.annotation_target)
        for alt in req.alternatives:
            if alt.annotation_target:
                all_targets_to_process.append(alt.annotation_target)

        for target in all_targets_to_process:
            content: Optional[str] = None
            source_id_for_log: str = f"target {target.id}"
            if target.completion_response:
                content = target.completion_response.choice_content
                source_id_for_log = f"response {target.completion_response.id}"
            elif target.completion_alternative:
                content = target.completion_alternative.alternative_content
                source_id_for_log = f"alternative {target.completion_alternative.id}"

            if content is None:
                logger.warning(f"Target {source_id_for_log} for request {req_id_str} has no associated content. Skipping for DPO.")
                continue

            if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                sft_targets_with_content.append((target, content))
            
            if is_dpo_negative_example(target, active_schema=active_schema_content, threshold=dpo_negative_threshold):
                dpo_negative_targets_with_content.append((target, content))

        if sft_targets_with_content and dpo_negative_targets_with_content:
            base_messages_data = req.messages
            if not isinstance(base_messages_data, list):
                 logger.warning(f"Request {req_id_str} messages field is not a list, skipping for DPO.")
                 continue
            try:
                input_messages = [
                    SftMessageSchema(role=msg.get("role"), content=msg.get("content"))
                    for msg in base_messages_data
                    if isinstance(msg, dict) and 'role' in msg and 'content' in msg
                ]
            except Exception as e:
                logger.warning(f"Failed to parse base messages for request {req_id_str}: {e}, skipping for DPO.")
                continue
            
            dpo_input = DpoInputSchema(messages=input_messages)

            for sft_target, preferred_content_str in sft_targets_with_content:
                preferred_msg = DpoAssistantMessageSchema(content=preferred_content_str)
                for neg_target, non_preferred_content_str in dpo_negative_targets_with_content:
                    if sft_target.id == neg_target.id: # Ensure preferred and non-preferred are from different targets
                        continue
                    
                    non_preferred_msg = DpoAssistantMessageSchema(content=non_preferred_content_str)
                    
                    dpo_example = DpoExampleSchema(
                        input=dpo_input,
                        preferred_output=[preferred_msg],
                        non_preferred_output=[non_preferred_msg]
                    )
                    dpo_dataset.append(dpo_example)
                    logger.debug(f"Added DPO entry for request {req_id_str}: preferred target {sft_target.id}, non-preferred target {neg_target.id}")
    
    logger.info(f"Generated {len(dpo_dataset)} DPO examples for project {project_id}.")
    return dpo_dataset

async def _generate_project_dpo_data_for_hub(
    project_id: uuid.UUID,
    db: AsyncSession,
    sft_threshold: float,
    dpo_negative_threshold: float
) -> List[Dict[str, Any]]:
    """
    Generates DPO data formatted for Hugging Face Hub upload.
    Each item contains 'chosen' and 'rejected' conversations, and their scores.
    """
    logger.info(f"Generating DPO data for Hub for project {project_id} (SFT >={sft_threshold}, DPO <{dpo_negative_threshold})")
    hub_dpo_dataset: List[Dict[str, Any]] = []

    active_schema_content: Optional[Dict[str, Any]] = None
    try:
        stmt_schema = (
            select(models.ProjectJsonSchema)
            .where(models.ProjectJsonSchema.project_id == project_id)
            .where(models.ProjectJsonSchema.is_active == True)
            .order_by(models.ProjectJsonSchema.created_at.desc())
        )
        result_schema = await db.execute(stmt_schema)
        active_schema_obj = result_schema.scalars().first()
        if active_schema_obj:
            active_schema_content = active_schema_obj.schema_content
    except Exception as schema_exc:
        logger.error(f"Error fetching active schema for DPO Hub dataset (project {project_id}): {schema_exc}", exc_info=True)

    stmt_requests = (
        select(models.CompletionsRequest)
        .where(models.CompletionsRequest.project_id == project_id)
        .options(
            selectinload(models.CompletionsRequest.completion_response)
            .selectinload(models.CompletionResponse.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            ),
            selectinload(models.CompletionsRequest.alternatives)
            .selectinload(models.CompletionAlternative.annotation_target)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
            )
        )
        .order_by(models.CompletionsRequest.id)
    )
    result = await db.execute(stmt_requests)
    requests = result.scalars().unique().all()
    logger.debug(f"Fetched {len(requests)} requests for DPO Hub dataset generation.")

    for req in requests:
        req_id_str = str(req.id)
        
        base_messages_data = req.messages
        if not isinstance(base_messages_data, list):
            logger.warning(f"Request {req_id_str} messages field is not a list, skipping for DPO Hub.")
            continue
        try:
            # Convert to SftMessageSchema dicts for consistency with HF format
            base_user_messages = [
                SftMessageSchema(role=msg.get("role"), content=msg.get("content")).model_dump()
                for msg in base_messages_data
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg
            ]
        except Exception as e:
            logger.warning(f"Failed to parse base messages for request {req_id_str} for DPO Hub: {e}, skipping.")
            continue

        sft_targets_info: List[Tuple[models.AnnotationTarget, str, float]] = [] # target, content, avg_reward
        dpo_neg_targets_info: List[Tuple[models.AnnotationTarget, str, float]] = [] # target, content, avg_reward

        all_targets_to_process: List[models.AnnotationTarget] = []
        if req.completion_response and req.completion_response.annotation_target:
            all_targets_to_process.append(req.completion_response.annotation_target)
        for alt in req.alternatives:
            if alt.annotation_target:
                all_targets_to_process.append(alt.annotation_target)

        for target in all_targets_to_process:
            content: Optional[str] = None
            if target.completion_response: content = target.completion_response.choice_content
            elif target.completion_alternative: content = target.completion_alternative.alternative_content

            if not content or not target.annotations: continue

            total_reward = sum(ann.reward for ann in target.annotations if ann.reward is not None)
            num_annotations_with_reward = sum(1 for ann in target.annotations if ann.reward is not None)
            if num_annotations_with_reward == 0: continue
            average_reward = total_reward / len(target.annotations)


            if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                sft_targets_info.append((target, content, average_reward))
            
            if is_dpo_negative_example(target, active_schema=active_schema_content, threshold=dpo_negative_threshold):
                dpo_neg_targets_info.append((target, content, average_reward))

        if sft_targets_info and dpo_neg_targets_info:
            for sft_target, preferred_content, sft_score in sft_targets_info:
                chosen_assistant_msg = SftMessageSchema(role="assistant", content=preferred_content).model_dump()
                chosen_conversation = base_user_messages + [chosen_assistant_msg]

                for neg_target, non_preferred_content, dpo_neg_score in dpo_neg_targets_info:
                    if sft_target.id == neg_target.id: # Cannot be the same target
                        continue
                    
                    rejected_assistant_msg = SftMessageSchema(role="assistant", content=non_preferred_content).model_dump()
                    rejected_conversation = base_user_messages + [rejected_assistant_msg]
                    
                    hub_dpo_dataset.append({
                        "chosen": chosen_conversation,
                        "rejected": rejected_conversation,
                        "score_chosen": sft_score,
                        "score_rejected": dpo_neg_score,
                    })
                    logger.debug(f"Added DPO Hub entry for req {req_id_str}: chosen target {sft_target.id}, rejected target {neg_target.id}")
    
    logger.info(f"Generated {len(hub_dpo_dataset)} DPO examples for Hub for project {project_id}.")
    return hub_dpo_dataset


router = APIRouter(
    prefix="/mock-next",
    tags=["Mock Data for Next.js Frontend"],
)

@router.get("/{project_id}/requests-summary", response_model=List[MockRequestSummary])
async def get_requests_summary(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
    sft_threshold: float = Query(0.75, description="Minimum average reward for SFT examples."),
    dpo_negative_threshold: float = Query(0.25, description="Maximum average reward for DPO negative examples.") # Add DPO threshold
):
    """
    Retrieves a summary of completion requests for the specified project.
    Calculates SFT and DPO status based on annotations and schema compliance.
    Requires the user to be a member of the project.
    """
    logger.info(f"Fetching requests summary for project ID: {project_id} for user {membership.user_id}")

    try:
        # --- Fetch Active Schema Once (no changes needed here) ---
        active_schema_content: Optional[Dict[str, Any]] = None
        try:
            stmt_schema = (
                select(models.ProjectJsonSchema)
                .where(models.ProjectJsonSchema.project_id == project_id)
                .where(models.ProjectJsonSchema.is_active == True)
                .order_by(models.ProjectJsonSchema.created_at.desc())
            )
            result_schema = await db.execute(stmt_schema)
            active_schema_obj = result_schema.scalars().first()
            if active_schema_obj:
                active_schema_content = active_schema_obj.schema_content
                logger.debug(f"Found active schema {active_schema_obj.id} for request summary checks.")
            else:
                logger.debug(f"No active schema found for project {project_id}. Status checks will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema for request summary (project {project_id}): {schema_exc}", exc_info=True)
        # --- End Fetch Active Schema ---

        # --- Query (no changes needed here) ---
        stmt_requests = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.project_id == project_id)
            .outerjoin(models.CompletionResponse, models.CompletionsRequest.completion_response)
            .options(
                selectinload(models.CompletionsRequest.completion_response)
                .selectinload(models.CompletionResponse.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                ),
                selectinload(models.CompletionsRequest.alternatives)
                .selectinload(models.CompletionAlternative.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                )
            )
            .order_by(
                models.CompletionResponse.created.desc().nullslast(),
                models.CompletionsRequest.id.desc()
            )
        )
        # --- End Query ---

        result = await db.execute(stmt_requests)
        requests = result.scalars().unique().all()

        if not requests:
            logger.info(f"No completion requests found for project {project_id}")
            return []

        summary_list: List[MockRequestSummary] = []
        for req in requests:
            req_id_str = str(req.id)

            # --- Timestamp and Name/Question Logic (unchanged) ---
            timestamp_str = "N/A"
            if req.completion_response and req.completion_response.created:
                timestamp_str = format_timestamp(req.completion_response.created)
            elif req.alternatives:
                 try:
                     earliest_alt_ts = min(alt.created_at for alt in req.alternatives if alt.created_at)
                     timestamp_str = format_timestamp(earliest_alt_ts)
                 except (ValueError, TypeError):
                     pass

            name = f"Request {req_id_str[:8]}..."
            question = "N/A"
            if req.messages and isinstance(req.messages, list) and len(req.messages) > 0:
                user_messages_content = [
                    msg.get("content") for msg in reversed(req.messages) if msg.get("role") == "user" and msg.get("content")
                ]
                if user_messages_content:
                    question = user_messages_content[0]
                    name = (question[:50] + '...') if len(question) > 50 else question
                elif req.messages[-1].get("content"):
                    question = req.messages[-1].get("content")
                    name = (question[:50] + '...') if len(question) > 50 else question
            # --- End Timestamp and Name/Question Logic ---

            total_responses = 0
            annotated_responses_count = 0
            request_sft_status: RequestStatus = "none"
            # --- NEW: Initialize DPO status ---
            request_dpo_status: RequestStatus = "none"
            # --- End NEW ---

            targets_to_check: List[models.AnnotationTarget] = []
            if req.completion_response and req.completion_response.annotation_target:
                targets_to_check.append(req.completion_response.annotation_target)
            if req.alternatives:
                for alt in req.alternatives:
                    if alt.annotation_target:
                        targets_to_check.append(alt.annotation_target)

            total_responses = len(targets_to_check)

            # --- Calculate SFT Status (check only if not already complete) ---
            found_sft_for_request = False
            for target in targets_to_check:
                if target.annotations:
                    annotated_responses_count += 1
                    if not found_sft_for_request:
                        if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                            found_sft_for_request = True
                            # Don't break here, need to count all annotated responses

            if found_sft_for_request:
                request_sft_status = "complete"
            elif annotated_responses_count > 0:
                 request_sft_status = "partial" # If annotated but none are SFT
            # else remains "none"

            # --- NEW: Calculate DPO Status using is_dpo_ready ---
            if is_dpo_ready(
                request=req, # Pass the whole request object
                active_schema=active_schema_content,
                sft_threshold=sft_threshold,
                dpo_negative_threshold=dpo_negative_threshold
            ):
                request_dpo_status = "complete"
            # else remains "none" (no partial state defined for DPO readiness)
            # --- End NEW ---

            summary = MockRequestSummary(
                id=req_id_str,
                name=name,
                question=question,
                totalResponses=total_responses,
                annotatedResponses=annotated_responses_count,
                timestamp=timestamp_str,
                sftStatus=request_sft_status,
                dpoStatus=request_dpo_status, # Use calculated DPO status
            )
            summary_list.append(summary)

        logger.info(f"Returning {len(summary_list)} request summaries for project {project_id}")
        return summary_list

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error fetching request summaries for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve request summaries due to an internal error."
        )

# ... after download_sft_dataset_jsonl endpoint ...
# ... existing imports ...
import os
# ... existing code ...


class PushToHubResponse(BaseModel):
    success: bool
    message: str
    dataset_path: Optional[str] = None

class PushToHubRequest(BaseModel):
    hf_username : Optional[str] = None
    hf_write_access_token : Optional[str] = None
    do_push : Optional[bool] = False

@router.post(
    "/{project_id}/push-sft-dataset-to-hub",
    response_model=PushToHubResponse,
    summary="Generate SFT dataset for the project and push it to Hugging Face Hub." # Updated summary
)
async def push_sft_dataset_to_hub(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    request_body: PushToHubRequest = Body(...),
    sft_threshold: float = Query(0.75, description="The minimum average reward threshold for SFT examples."),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Generates the SFT dataset based on project annotations and criteria,
    formats it, and optionally pushes it to a Hugging Face Hub repository.
    """
    logger.info(f"Request to generate and potentially push SFT dataset for project {project_id} by user {membership.user_id}. do_push={request_body.do_push}, threshold={sft_threshold}")

    # --- Hub Configuration (Consider making more dynamic/secure) ---
    # Example: Get token from environment variable
    hf_write_access_token = request_body.hf_write_access_token #"os.getenv("HF_WRITE_TOKEN") # Use environment variable
    hf_username = request_body.hf_username # Optional: Get username from env too
    # Make dataset name unique and informative
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    hf_dataset_name = f"intercebd-sft-proj-{project_id}-{timestamp_str}"
    hf_dataset_path = f"{hf_username}/{hf_dataset_name}"
    hf_dataset_private = False # Or make this configurable
    # --- End Hub Configuration ---

    try:
        # --- Generate Actual SFT Data ---
        sft_data: List[SftConversationSchema] = await _generate_project_sft_data(
            project_id=project_id,
            db=db,
            sft_threshold=sft_threshold
        )

        if not sft_data:
            logger.info(f"No SFT data generated for project {project_id} with threshold {sft_threshold}. Nothing to push.")
            return PushToHubResponse(
                success=False, # Indicate failure due to no data
                message=f"No SFT examples found for project {project_id} meeting the threshold criteria. No dataset pushed.",
                dataset_path=None
            )
        # --- End Generate Actual SFT Data ---

        # --- Create Hugging Face Dataset ---
        # Convert Pydantic models to dictionaries
        data_list = [conv.model_dump() for conv in sft_data]

        hf_dataset = Dataset.from_list(data_list)
        # Removed the add_uuid mapping as the conversation structure is the data


        def add_uuid(example):
            return {"id": str(uuid.uuid4())}

        # Apply the function to add the 'id' column
        hf_dataset = hf_dataset.map(add_uuid)

        logger.info(f"Prepared dataset with {len(hf_dataset)} SFT entries for {hf_dataset_path}")
        # --- End Create Hugging Face Dataset ---

        if request_body.do_push:
            print('SFT-TO-HUB inside do-push')
            if not hf_write_access_token:
                 logger.error("Hugging Face write token (HF_WRITE_TOKEN environment variable) is not configured. Cannot push.")
                 # Avoid exposing token details in the error message
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail="Hugging Face Hub token not configured on the server."
                 )

            logger.info(f"Attempting to push dataset to Hugging Face Hub: {hf_dataset_path}")
            try:
                # Ensure the user is logged in if using default token inference
                # huggingface_hub.login(token=hf_write_access_token) # Explicit login might be needed depending on environment

                hf_dataset.push_to_hub(
                    repo_id=hf_dataset_path,
                    token=hf_write_access_token, # Pass the token explicitly
                    private=hf_dataset_private
                )
                logger.info(f"Successfully pushed dataset to {hf_dataset_path}")
                return PushToHubResponse(
                    success=True,
                    message=f"Successfully generated and pushed {len(hf_dataset)} SFT examples to {hf_dataset_path}",
                    dataset_path=hf_dataset_path
                )
            except Exception as e:
                logger.exception(f"Error pushing dataset to Hugging Face Hub ({hf_dataset_path}): {e}", exc_info=True)
                # Provide a more generic error to the client
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to push dataset to Hugging Face Hub. Check server logs for details."
                )
        else:
            logger.info("Dataset prepared but not pushed (do_push=False).")
            return PushToHubResponse(
                success=True, # Success in preparing the data
                message=f"Dataset with {len(hf_dataset)} SFT examples prepared successfully but not pushed to Hub.",
                dataset_path=hf_dataset_path # Return the intended path
            )

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        logger.exception(f"Error preparing or handling SFT dataset for push (project {project_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while preparing the SFT dataset. Check server logs."
        )

@router.post(
    "/{project_id}/push-dpo-dataset-to-hub",
    response_model=PushToHubResponse,
    summary="Generate DPO dataset for the project and push it to Hugging Face Hub."
)
async def push_dpo_dataset_to_hub(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    request_body: PushToHubRequest = Body(...),
    sft_threshold: float = Query(0.75, description="Minimum average reward for SFT examples (chosen)."),
    dpo_negative_threshold: float = Query(0.25, description="Maximum average reward for DPO negative examples (rejected)."),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Generates the DPO dataset based on project annotations and criteria,
    formats it for Hugging Face (chosen/rejected pairs), and optionally pushes it
    to a Hugging Face Hub repository.
    """
    logger.info(f"Request to generate and potentially push DPO dataset for project {project_id} by user {membership.user_id}. do_push={request_body.do_push}")

    hf_write_access_token = request_body.hf_write_access_token
    hf_username = request_body.hf_username
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    hf_dataset_name = f"intercebd-dpo-proj-{project_id}-{timestamp_str}" # DPO specific name
    
    if not hf_username: # Default to a generic username if not provided, or handle as error
        # Fallback or error if username is critical for your setup
        # For this example, let's assume it might be optional or derived elsewhere if not provided
        # but for a real application, you'd likely require it or have a default.
        # hf_username = "default-hf-user" # Placeholder if you have a default org/user
        logger.warning("Hugging Face username not provided in request body. Dataset path might be incomplete if pushed.")
        # If hf_username is strictly required for push_to_hub:
        if request_body.do_push:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hugging Face username is required to push the dataset."
            )
        hf_dataset_path = hf_dataset_name # Path without username if not provided
    else:
        hf_dataset_path = f"{hf_username}/{hf_dataset_name}"

    hf_dataset_private = False 

    try:
        dpo_data_for_hub: List[Dict[str, Any]] = await _generate_project_dpo_data_for_hub(
            project_id=project_id,
            db=db,
            sft_threshold=sft_threshold,
            dpo_negative_threshold=dpo_negative_threshold
        )

        if not dpo_data_for_hub:
            logger.info(f"No DPO data generated for Hub for project {project_id}. Nothing to push.")
            return PushToHubResponse(
                success=False,
                message=f"No DPO examples found for project {project_id} meeting the criteria. No dataset pushed.",
                dataset_path=None
            )

        # Create Hugging Face Dataset from the list of dicts
        hf_dataset = Dataset.from_list(dpo_data_for_hub)

        # Add UUIDs if needed (as per your SFT example)
        def add_uuid(example):
            return {"id": str(uuid.uuid4())}
        hf_dataset = hf_dataset.map(add_uuid)

        logger.info(f"Prepared DPO dataset with {len(hf_dataset)} entries for {hf_dataset_path}")

        if request_body.do_push:
            if not hf_write_access_token:
                 logger.error("Hugging Face write token not provided. Cannot push DPO dataset.")
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST, # Or 500 if server misconfiguration
                     detail="Hugging Face Hub write access token not provided in the request."
                 )
            if not hf_username: # Re-check, as path construction depends on it for typical HF repos
                logger.error("Hugging Face username not provided. Cannot push DPO dataset to a user/org repository.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hugging Face username is required to push the dataset to a user/organization repository."
                )


            logger.info(f"Attempting to push DPO dataset to Hugging Face Hub: {hf_dataset_path}")
            try:
                hf_dataset.push_to_hub(
                    repo_id=hf_dataset_path,
                    token=hf_write_access_token,
                    private=hf_dataset_private
                )
                logger.info(f"Successfully pushed DPO dataset to {hf_dataset_path}")
                return PushToHubResponse(
                    success=True,
                    message=f"Successfully generated and pushed {len(hf_dataset)} DPO examples to {hf_dataset_path}",
                    dataset_path=hf_dataset_path
                )
            except Exception as e:
                logger.exception(f"Error pushing DPO dataset to Hugging Face Hub ({hf_dataset_path}): {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to push DPO dataset to Hugging Face Hub. Check server logs for details."
                )
        else:
            logger.info("DPO dataset prepared but not pushed (do_push=False).")
            return PushToHubResponse(
                success=True,
                message=f"DPO dataset with {len(hf_dataset)} examples prepared successfully but not pushed to Hub.",
                dataset_path=hf_dataset_path # Return the intended path
            )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error preparing or handling DPO dataset for push (project {project_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while preparing the DPO dataset. Check server logs."
        )

# ... rest of the file ...
# ... rest of the file ...# ... rest of the file ...

@router.get("/{project_id}/requests/{request_id}", response_model=MockRequestDetail)
async def get_request_details(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    request_id: uuid.UUID = Path(..., description="The UUID of the request"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership)
):
    """
    Retrieves full details for a specific completion request within a project.
    Also fetches the current project schema and validates response content against it.
    Requires the user to be a member of the project.
    """
    logger.info(f"Fetching details for request ID: {request_id} in project {project_id} for user {membership.user_id}")

    # --- Fetch Active Schema Concurrently (or sequentially) ---
    active_schema_content: Optional[Dict[str, Any]] = None
    try:
        stmt_schema = (
            select(models.ProjectJsonSchema)
            .where(models.ProjectJsonSchema.project_id == project_id)
            .where(models.ProjectJsonSchema.is_active == True)
            .order_by(models.ProjectJsonSchema.created_at.desc())
        )
        result_schema = await db.execute(stmt_schema)
        active_schema_obj = result_schema.scalars().first()
        if active_schema_obj:
            active_schema_content = active_schema_obj.schema_content
            logger.info(f"Found active schema {active_schema_obj.id} for validation.")
        else:
            logger.info(f"No active schema found for project {project_id}. Skipping schema validation.")
    except Exception as schema_exc:
        # Log error but don't fail the request, just skip schema validation
        logger.error(f"Error fetching active schema for project {project_id}: {schema_exc}", exc_info=True)
    # --- End Fetch Active Schema ---

    try:
        # --- Fetch Request Details ---
        stmt_req = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.id == request_id)
            .where(models.CompletionsRequest.project_id == project_id)
            .options(
                selectinload(models.CompletionsRequest.completion_response)
                .selectinload(models.CompletionResponse.annotation_target)
                .selectinload(models.AnnotationTarget.annotations),
                selectinload(models.CompletionsRequest.alternatives)
                .selectinload(models.CompletionAlternative.annotation_target)
                .selectinload(models.AnnotationTarget.annotations)
            )
        )
        result_req = await db.execute(stmt_req)
        req = result_req.scalars().first()
        # --- End Fetch Request Details ---

        if not req:
            logger.warning(f"CompletionsRequest with ID {request_id} not found in project {project_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found in this project.")

        req_id_str = str(req.id)
        project_id_str = str(req.project_id)
        request_timestamp_str = "N/A"
        if req.completion_response and req.completion_response.created:
            request_timestamp_str = format_timestamp(req.completion_response.created)
        elif req.alternatives:
            try:
                earliest_alt_ts = min(alt.created_at for alt in req.alternatives if alt.created_at)
                request_timestamp_str = format_timestamp(earliest_alt_ts)
            except (ValueError, TypeError):
                pass

        request_data = RequestDetailData(
            id=req_id_str,
            project_id=project_id_str,
            messages=[Message(**msg) for msg in req.messages] if req.messages else [],
            model=req.model or "Unknown",
            response_format=req.response_format,
            request_timestamp=request_timestamp_str
        )

        # --- Map Responses with Schema Validation ---
        main_response_detail: Optional[ResponseDetail] = None
        if req.completion_response:
            try:
                main_response_detail = map_to_response_detail(
                    req.completion_response,
                    req.model or "Unknown",
                    active_schema=active_schema_content
                )
            except Exception as map_err:
                logger.error(f"Error mapping main response for request {req_id_str}: {map_err}", exc_info=True)

        alternative_response_details: List[ResponseDetail] = []
        if req.alternatives:
            for alt in req.alternatives:
                try:
                    alt_detail = map_to_response_detail(
                        alt,
                        req.model or "Unknown",
                        active_schema=active_schema_content
                    )
                    alternative_response_details.append(alt_detail)
                except Exception as map_err:
                    logger.error(f"Error mapping alternative response {alt.id} for request {req_id_str}: {map_err}", exc_info=True)
        # --- End Mapping ---

        name = f"Request {req_id_str[:8]}..."
        if req.messages and isinstance(req.messages, list) and len(req.messages) > 0:
            user_messages_content = [
                msg.get("content") for msg in reversed(req.messages) if msg.get("role") == "user" and msg.get("content")
            ]
            if user_messages_content:
                question = user_messages_content[0]
                name = (question[:50] + '...') if len(question) > 50 else question
            elif req.messages[-1].get("content"):
                question = req.messages[-1].get("content")
                name = (question[:50] + '...') if len(question) > 50 else question

        if not main_response_detail:
            logger.warning(f"Main response missing or failed to map for request {req_id_str}. Returning alternatives only.")
            if not alternative_response_details:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request found, but no valid responses associated.")
            main_response_detail = ResponseDetail(
                id="N/A", content="Main response missing", model=req.model or "Unknown",
                created="N/A", annotations=[], metadata=None, is_json=False, obeys_schema=None
            )

        response_detail = MockRequestDetail(
            id=req_id_str,
            name=name,
            pairNumber=1,
            request=request_data,
            mainResponse=main_response_detail,
            alternativeResponses=alternative_response_details
        )

        return response_detail

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error fetching details for request {request_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve request details due to an internal error."
        )

@router.post(
    "/{project_id}/annotation-targets/{annotation_target_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new annotation for a specific target within a project."
)
async def create_annotation(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    annotation_target_id: uuid.UUID = Path(..., description="The UUID of the AnnotationTarget to annotate"),
    request_data: CreateAnnotationRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Creates a new annotation record for a given AnnotationTarget.
    Requires the user to be a member of the project associated with the target.
    The user performing the annotation is automatically recorded if logged in.
    """
    logger.info(f"Attempting to create annotation for target {annotation_target_id} in project {project_id} by user {current_user.id if current_user else 'Guest/Unknown'}")

    stmt_target = (
        select(models.AnnotationTarget)
        .where(models.AnnotationTarget.id == annotation_target_id)
        .options(selectinload(models.AnnotationTarget.annotations))
    )
    result_target = await db.execute(stmt_target)
    target = result_target.scalars().first()

    if not target:
        logger.warning(f"AnnotationTarget with ID {annotation_target_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation target not found.")

    annotator_user_id: Optional[uuid.UUID] = current_user.id if current_user else None

    try:
        new_annotation = models.CompletionAnnotation(
            user_id=annotator_user_id,
            reward=request_data.reward,
            annotation_metadata=request_data.annotation_metadata
        )
        db.add(new_annotation)
        await db.flush()

        target.annotations.append(new_annotation)

        await db.commit()
        await db.refresh(new_annotation)
        logger.info(f"Successfully created annotation {new_annotation.id} for target {annotation_target_id}")

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error creating or linking annotation for target {annotation_target_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save annotation due to an internal error."
        )

    response_data = AnnotationResponse(
        id=new_annotation.id,
        timestamp=new_annotation.timestamp,
        user_id=new_annotation.user_id,
        reward=new_annotation.reward,
        annotation_metadata=new_annotation.annotation_metadata,
        annotation_target_id=annotation_target_id
    )

    return response_data

@router.delete(
    "/{project_id}/annotation-targets/{annotation_target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an AnnotationTarget and its associated CompletionResponse or CompletionAlternative."
)
async def delete_annotation_target(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    annotation_target_id: uuid.UUID = Path(..., description="The UUID of the AnnotationTarget to delete"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Deletes an AnnotationTarget. Due to cascade settings in the models,
    this should also delete the linked CompletionResponse or CompletionAlternative.
    Requires the user to be a member of the project.
    """
    logger.info(f"Attempting to delete AnnotationTarget {annotation_target_id} in project {project_id} by user {membership.user_id}")

    stmt = select(models.AnnotationTarget).where(models.AnnotationTarget.id == annotation_target_id)
    result = await db.execute(stmt)
    target_to_delete = result.scalars().first()

    if not target_to_delete:
        logger.warning(f"AnnotationTarget with ID {annotation_target_id} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation target not found.")

    try:
        await db.delete(target_to_delete)
        await db.commit()
        logger.info(f"Successfully deleted AnnotationTarget {annotation_target_id}")
        return None

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error deleting AnnotationTarget {annotation_target_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete annotation target due to an internal error."
        )

@router.delete(
    "/{project_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific CompletionAnnotation."
)
async def delete_annotation(
    project_id: uuid.UUID = Path(..., description="The UUID of the project (for authorization)"),
    annotation_id: uuid.UUID = Path(..., description="The UUID of the CompletionAnnotation to delete"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Deletes a specific CompletionAnnotation record by its ID.
    Requires the user to be a member of the project associated with the annotation's target.
    """
    logger.info(f"Attempting to delete Annotation {annotation_id} within project scope {project_id} by user {membership.user_id}")

    CR = models.CompletionResponse
    CA = models.CompletionAlternative
    AT = models.AnnotationTarget
    Ann = models.CompletionAnnotation
    ReqFromResp = aliased(models.CompletionsRequest)
    ReqFromAlt = aliased(models.CompletionsRequest)

    stmt = (
        select(Ann)
        .join(Ann.annotation_targets)
        .outerjoin(CR, AT.completion_response)
        .outerjoin(CA, AT.completion_alternative)
        .outerjoin(ReqFromResp, CR.completion_request)
        .outerjoin(ReqFromAlt, CA.original_completion_request)
        .where(Ann.id == annotation_id)
        .where(
            (ReqFromResp.project_id == project_id) |
            (ReqFromAlt.project_id == project_id)
        )
        .limit(1)
    )

    result = await db.execute(stmt)
    annotation_to_delete = result.scalars().first()

    if not annotation_to_delete:
        logger.warning(f"Annotation with ID {annotation_id} not found or not accessible within project {project_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found.")

    try:
        await db.delete(annotation_to_delete)
        await db.commit()
        logger.info(f"Successfully deleted Annotation {annotation_id}")
        return None

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error deleting Annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete annotation due to an internal error."
        )

@router.post(
    "/{project_id}/requests/{request_id}/alternatives",
    response_model=CreateAlternativeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new alternative response for a specific request."
)
async def create_alternative(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    request_id: uuid.UUID = Path(..., description="The UUID of the original CompletionsRequest"),
    request_data: CreateAlternativeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Creates a new CompletionAlternative for an existing CompletionsRequest.
    Also creates the associated AnnotationTarget.
    Requires the user to be a member of the project.
    """
    logger.info(f"Attempting to create alternative for request {request_id} in project {project_id} by user {membership.user_id}")

    stmt_req = select(models.CompletionsRequest).where(
        models.CompletionsRequest.id == request_id,
        models.CompletionsRequest.project_id == project_id
    )
    result_req = await db.execute(stmt_req)
    original_request = result_req.scalars().first()

    if not original_request:
        logger.warning(f"Original CompletionsRequest {request_id} not found in project {project_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original request not found in this project.")

    try:
        new_annotation_target = models.AnnotationTarget()
        db.add(new_annotation_target)
        await db.flush()
        target_id = new_annotation_target.id

        new_alternative = models.CompletionAlternative(
            original_completion_request_id=request_id,
            project_id=project_id,
            alternative_content=request_data.alternative_content,
            annotation_target_id=target_id,
        )
        db.add(new_alternative)

        await db.flush([new_alternative])
        alternative_id = new_alternative.id
        if alternative_id is None:
            logger.error("!!! Critical: Alternative ID is None after explicit flush !!!")
            raise HTTPException(status_code=500, detail="Failed to generate alternative ID.")
        logger.debug(f"Alternative ID after flush: {alternative_id}")

        await db.commit()
        logger.debug(f"Committed alternative ID: {alternative_id}")

        stmt_load = (
            select(models.CompletionAlternative)
            .where(models.CompletionAlternative.id == alternative_id)
            .options(
                selectinload(models.CompletionAlternative.annotation_target)
                .selectinload(models.AnnotationTarget.annotations)
            )
        )
        result_load = await db.execute(stmt_load)
        loaded_alternative = result_load.scalars().one()

        logger.info(f"Successfully created alternative {loaded_alternative.id} for request {request_id}")

        response_data = map_to_response_detail(loaded_alternative, original_request.model or "Unknown")
        return response_data

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error creating alternative for request {request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save alternative response due to an internal error."
        )

@router.post(
    "/{project_id}/schemas",
    response_model=ProjectJsonSchemaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new JSON schema version and set it as the project's current schema."
)
async def create_and_set_project_schema(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    schema_data: JsonSchemaContent = Body(...),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Creates a new ProjectJsonSchema record, marks it as active,
    and deactivates all other schemas for the project.
    Validates that the provided content is a valid JSON Schema document.
    Relies on the 'is_active' flag and creation timestamp.
    """
    logger.info(f"Attempting to create and set new schema for project {project_id} by user {membership.user_id}")

    try:
        validate_jsonschema(instance=schema_data.schema_content, schema=Draft7Validator.META_SCHEMA)
        logger.debug(f"Schema content for project {project_id} validated successfully against meta-schema.")
    except JsonSchemaValidationError as e:
        logger.warning(f"Invalid JSON Schema provided for project {project_id}: {e.message}", exc_info=False)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON Schema: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during JSON Schema validation for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during schema validation."
        )

    try:
        stmt_deactivate = (
            update(models.ProjectJsonSchema)
            .where(models.ProjectJsonSchema.project_id == project_id)
            .where(models.ProjectJsonSchema.is_active == True)
            .values(is_active=False)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt_deactivate)
        logger.debug(f"Deactivated {result.rowcount} previous schema(s) for project {project_id}")

        new_schema = models.ProjectJsonSchema(
            project_id=project_id,
            schema_content=schema_data.schema_content,
            is_active=True
        )
        db.add(new_schema)
        await db.flush()

        logger.debug(f"Project {project_id}: Attempting to commit new active schema {new_schema.id}")
        await db.commit()
        logger.debug(f"Project {project_id}: Commit successful. New active schema is {new_schema.id}")

        await db.refresh(new_schema)

        logger.info(f"Successfully created schema {new_schema.id} and set as active for project {project_id}")
        return new_schema

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Database integrity error creating schema for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: {e.orig}"
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error during database operation for schema creation (project {project_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save schema due to an internal database error."
        )

@router.get(
    "/{project_id}/schemas/current",
    response_model=ProjectJsonSchemaResponse,
    summary="Get the currently active JSON schema for the project (latest active version)."
)
async def get_current_project_schema(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Retrieves the most recently created JSON schema for the project
    where the 'is_active' flag is True.
    """
    logger.info(f"Fetching latest active schema for project {project_id} by user {membership.user_id}")

    stmt = (
        select(models.ProjectJsonSchema)
        .where(models.ProjectJsonSchema.project_id == project_id)
        .where(models.ProjectJsonSchema.is_active == True)
        .order_by(models.ProjectJsonSchema.created_at.desc())
    )
    result = await db.execute(stmt)
    current_schema = result.scalars().first()

    if not current_schema:
        logger.info(f"Project {project_id} does not have an active schema.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active schema found for this project.")

    logger.info(f"Found latest active schema {current_schema.id} created at {current_schema.created_at} for project {project_id}")
    return current_schema

# Modify the is_sft_example function
def is_sft_example(
    target: models.AnnotationTarget,
    active_schema: Optional[Dict[str, Any]] = None,
    threshold: float = 0.75
) -> bool:
    """
    Determines if an annotation target qualifies as an SFT example.
    Checks average reward and, if an active schema is provided,
    also validates JSON format and schema compliance.

    Args:
        target: The AnnotationTarget object, potentially with loaded relationships.
        active_schema: The active JSON schema for the project, if any.
        threshold: The minimum average reward to qualify as SFT (default: 0.75)

    Returns:
        bool: True if the target qualifies as an SFT example, False otherwise
    """
    # 1. Check Annotations and Reward Average (always required)
    if not target.annotations:
        return False # Must have annotations

    total_reward = sum(annotation.reward for annotation in target.annotations if annotation.reward is not None)
    # Ensure we don't divide by zero if annotations exist but all rewards are None (unlikely but safe)
    num_annotations_with_reward = sum(1 for annotation in target.annotations if annotation.reward is not None)
    if num_annotations_with_reward == 0:
         return False # Cannot calculate average if no rewards are present

    average_reward = total_reward / len(target.annotations) # Use total count for average as before

    if average_reward < threshold:
        logger.debug(f"SFT Check Failed for target {target.id}: Average reward {average_reward} < {threshold}")
        return False # Failed reward threshold

    # 2. Check JSON and Schema if active_schema is provided
    if active_schema:
        logger.debug(f"SFT Check for target {target.id}: Active schema provided. Performing JSON/Schema validation.")
        content: Optional[str] = None
        source_id_for_log: str = f"target {target.id}"

        # Determine content source
        if target.completion_response:
            content = target.completion_response.choice_content
            source_id_for_log = f"response {target.completion_response.id}"
        elif target.completion_alternative:
            content = target.completion_alternative.alternative_content
            source_id_for_log = f"alternative {target.completion_alternative.id}"

        if not content:
            logger.debug(f"SFT Check Failed for {source_id_for_log}: No content found.")
            return False # No content to validate

        # Check if content is valid JSON
        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            logger.debug(f"SFT Check Failed for {source_id_for_log}: Content is not valid JSON.")
            return False # Not valid JSON

        # Validate against schema
        try:
            validate_jsonschema(instance=parsed_content, schema=active_schema)
            logger.debug(f"SFT Check Passed Schema Validation for {source_id_for_log}.")
        except JsonSchemaValidationError:
            logger.debug(f"SFT Check Failed for {source_id_for_log}: Content does not obey schema.")
            return False # Does not obey schema
        except Exception as e:
            # Catch other potential validation errors
            logger.warning(f"SFT Check encountered unexpected validation error for {source_id_for_log}: {e}")
            return False # Treat unexpected validation errors as failure

    # If all checks passed (reward threshold met, and schema checks passed if applicable)
    logger.debug(f"SFT Check Passed for target {target.id} (Reward >= {threshold} and Schema checks passed if applicable)")
    return True

# ... after is_sft_example function ...

def is_dpo_negative_example(
    target: models.AnnotationTarget,
    active_schema: Optional[Dict[str, Any]] = None,
    threshold: float = 0.25 # Default threshold for negative examples
) -> bool:
    """
    Determines if an annotation target qualifies as a DPO negative example.
    Checks average reward is BELOW the threshold and, if an active schema is provided,
    also validates JSON format and schema compliance.

    Args:
        target: The AnnotationTarget object, potentially with loaded relationships.
        active_schema: The active JSON schema for the project, if any.
        threshold: The maximum average reward to qualify as DPO negative (default: 0.25)

    Returns:
        bool: True if the target qualifies as a DPO negative example, False otherwise
    """
    # 1. Check Annotations and Reward Average (always required)
    if not target.annotations:
        return False # Must have annotations

    total_reward = sum(annotation.reward for annotation in target.annotations if annotation.reward is not None)
    num_annotations_with_reward = sum(1 for annotation in target.annotations if annotation.reward is not None)
    if num_annotations_with_reward == 0:
         return False # Cannot calculate average if no rewards are present

    average_reward = total_reward / len(target.annotations)

    # --- DPO Negative Check: Reward must be LESS THAN the threshold ---
    if average_reward >= threshold:
        logger.debug(f"DPO Negative Check Failed for target {target.id}: Average reward {average_reward} >= {threshold}")
        return False # Failed reward threshold (reward is too high)

    # 2. Check JSON and Schema if active_schema is provided (same logic as SFT)
    if active_schema:
        logger.debug(f"DPO Negative Check for target {target.id}: Active schema provided. Performing JSON/Schema validation.")
        content: Optional[str] = None
        source_id_for_log: str = f"target {target.id}"

        if target.completion_response:
            content = target.completion_response.choice_content
            source_id_for_log = f"response {target.completion_response.id}"
        elif target.completion_alternative:
            content = target.completion_alternative.alternative_content
            source_id_for_log = f"alternative {target.completion_alternative.id}"

        if not content:
            logger.debug(f"DPO Negative Check Failed for {source_id_for_log}: No content found.")
            return False

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            logger.debug(f"DPO Negative Check Failed for {source_id_for_log}: Content is not valid JSON.")
            return False

        try:
            validate_jsonschema(instance=parsed_content, schema=active_schema)
            logger.debug(f"DPO Negative Check Passed Schema Validation for {source_id_for_log}.")
        except JsonSchemaValidationError:
            logger.debug(f"DPO Negative Check Failed for {source_id_for_log}: Content does not obey schema.")
            return False
        except Exception as e:
            logger.warning(f"DPO Negative Check encountered unexpected validation error for {source_id_for_log}: {e}")
            return False

    # If all checks passed (reward is low enough, and schema checks passed if applicable)
    logger.debug(f"DPO Negative Check Passed for target {target.id} (Reward < {threshold} and Schema checks passed if applicable)")
    return True

# ... after is_dpo_negative_example function ...

def is_dpo_ready(
    request: models.CompletionsRequest,
    active_schema: Optional[Dict[str, Any]] = None,
    sft_threshold: float = 0.75,
    dpo_negative_threshold: float = 0.25
) -> bool:
    """
    Determines if a CompletionsRequest is ready for DPO.
    A request is DPO ready if it has at least one associated AnnotationTarget
    that qualifies as an SFT example AND at least one associated AnnotationTarget
    that qualifies as a DPO negative example.

    Args:
        request: The CompletionsRequest object, with relationships loaded.
        active_schema: The active JSON schema for the project, if any.
        sft_threshold: The minimum average reward for SFT examples.
        dpo_negative_threshold: The maximum average reward for DPO negative examples.

    Returns:
        bool: True if the request is DPO ready, False otherwise.
    """
    found_sft = False
    found_dpo_negative = False

    targets_to_check: List[models.AnnotationTarget] = []
    if request.completion_response and request.completion_response.annotation_target:
        targets_to_check.append(request.completion_response.annotation_target)
    if request.alternatives:
        for alt in request.alternatives:
            if alt.annotation_target:
                targets_to_check.append(alt.annotation_target)

    if not targets_to_check:
        logger.debug(f"Request {request.id} has no annotation targets, cannot be DPO ready.")
        return False # No targets to check

    for target in targets_to_check:
        if not found_sft:
            if is_sft_example(target, active_schema=active_schema, threshold=sft_threshold):
                found_sft = True
                logger.debug(f"DPO Ready Check for Request {request.id}: Found SFT example (target {target.id}).")

        if not found_dpo_negative:
            if is_dpo_negative_example(target, active_schema=active_schema, threshold=dpo_negative_threshold):
                found_dpo_negative = True
                logger.debug(f"DPO Ready Check for Request {request.id}: Found DPO Negative example (target {target.id}).")

        # Optimization: If both are found, no need to check further targets for this request
        if found_sft and found_dpo_negative:
            logger.debug(f"DPO Ready Check for Request {request.id}: Found both SFT and DPO Negative examples. Result: True.")
            return True

    # If loop finishes and we haven't found both
    logger.debug(f"DPO Ready Check for Request {request.id}: Finished checking targets. Found SFT: {found_sft}, Found DPO Negative: {found_dpo_negative}. Result: False.")
    return False

@router.get(
    "/{project_id}/annotation-targets/{annotation_target_id}/is-sft",
    response_model=bool,
    summary="Check if an annotation target qualifies as an SFT example."
)
async def check_if_sft_example(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    annotation_target_id: uuid.UUID = Path(..., description="The UUID of the annotation target to check"),
    threshold: float = Query(0.75, description="The minimum average reward threshold for SFT."),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Determines if an annotation target qualifies as an SFT example based on its annotations
    and schema compliance if an active schema exists.
    """
    logger.info(f"Checking if annotation target {annotation_target_id} is an SFT example (project: {project_id})")

    try:
        # --- Fetch Active Schema ---
        active_schema_content: Optional[Dict[str, Any]] = None
        try:
            stmt_schema = (
                select(models.ProjectJsonSchema)
                .where(models.ProjectJsonSchema.project_id == project_id)
                .where(models.ProjectJsonSchema.is_active == True)
                .order_by(models.ProjectJsonSchema.created_at.desc())
            )
            result_schema = await db.execute(stmt_schema)
            active_schema_obj = result_schema.scalars().first()
            if active_schema_obj:
                active_schema_content = active_schema_obj.schema_content
                logger.debug(f"Found active schema {active_schema_obj.id} for SFT check.")
            else:
                logger.debug(f"No active schema found for project {project_id}. SFT check will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema during SFT check for project {project_id}: {schema_exc}", exc_info=True)
            # Continue without schema validation if fetching fails
        # --- End Fetch Active Schema ---

        # Get the annotation target with relationships needed for is_sft_example
        stmt = (
            select(models.AnnotationTarget)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                selectinload(models.AnnotationTarget.completion_response),
                selectinload(models.AnnotationTarget.completion_alternative)
            )
            .where(models.AnnotationTarget.id == annotation_target_id)
        )
        result = await db.execute(stmt)
        target = result.scalars().first()

        if not target:
            logger.warning(f"Annotation target {annotation_target_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation target not found."
            )

        # --- Project Verification ---
        belongs_to_project = False
        stmt_check_response = (
            select(models.CompletionResponse.id)
            .join(models.CompletionsRequest, models.CompletionResponse.completion_request_id == models.CompletionsRequest.id)
            .where(models.CompletionResponse.annotation_target_id == annotation_target_id)
            .where(models.CompletionsRequest.project_id == project_id)
            .limit(1)
        )
        result_resp = await db.execute(stmt_check_response)
        if result_resp.scalar_one_or_none() is not None:
            belongs_to_project = True

        if not belongs_to_project:
            stmt_check_alt = (
                select(models.CompletionAlternative.id)
                .where(models.CompletionAlternative.annotation_target_id == annotation_target_id)
                .where(models.CompletionAlternative.project_id == project_id)
                .limit(1)
            )
            result_alt = await db.execute(stmt_check_alt)
            if result_alt.scalar_one_or_none() is not None:
                belongs_to_project = True

        if not belongs_to_project:
            logger.warning(f"Annotation target {annotation_target_id} not found in project {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation target not found in this project."
            )
        # --- End Project Verification ---

        # Determine if this is an SFT example using the updated function
        is_sft = is_sft_example(target, active_schema=active_schema_content, threshold=threshold)
        logger.info(f"Annotation target {annotation_target_id}: is_sft={is_sft} (threshold={threshold}, schema_checked={active_schema_content is not None})")

        return is_sft

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error checking if annotation target {annotation_target_id} is an SFT example: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to determine SFT status due to an internal error."
        )

@router.get(
    "/{project_id}/annotation-targets/{annotation_target_id}/is-dpo-negative",
    response_model=bool,
    summary="Check if an annotation target qualifies as a DPO negative example."
)
async def check_if_dpo_negative_example(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    annotation_target_id: uuid.UUID = Path(..., description="The UUID of the annotation target to check"),
    threshold: float = Query(0.25, description="The maximum average reward threshold for DPO negative."), # Default 0.25
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Determines if an annotation target qualifies as a DPO negative example based on its annotations
    (average reward < threshold) and schema compliance if an active schema exists.
    """
    logger.info(f"Checking if annotation target {annotation_target_id} is a DPO negative example (project: {project_id})")

    try:
        # --- Fetch Active Schema (same as is-sft endpoint) ---
        active_schema_content: Optional[Dict[str, Any]] = None
        try:
            stmt_schema = (
                select(models.ProjectJsonSchema)
                .where(models.ProjectJsonSchema.project_id == project_id)
                .where(models.ProjectJsonSchema.is_active == True)
                .order_by(models.ProjectJsonSchema.created_at.desc())
            )
            result_schema = await db.execute(stmt_schema)
            active_schema_obj = result_schema.scalars().first()
            if active_schema_obj:
                active_schema_content = active_schema_obj.schema_content
                logger.debug(f"Found active schema {active_schema_obj.id} for DPO negative check.")
            else:
                logger.debug(f"No active schema found for project {project_id}. DPO negative check will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema during DPO negative check for project {project_id}: {schema_exc}", exc_info=True)
        # --- End Fetch Active Schema ---

        # --- Fetch Target (same as is-sft endpoint) ---
        stmt = (
            select(models.AnnotationTarget)
            .options(
                selectinload(models.AnnotationTarget.annotations),
                selectinload(models.AnnotationTarget.completion_response),
                selectinload(models.AnnotationTarget.completion_alternative)
            )
            .where(models.AnnotationTarget.id == annotation_target_id)
        )
        result = await db.execute(stmt)
        target = result.scalars().first()

        if not target:
            logger.warning(f"Annotation target {annotation_target_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation target not found."
            )
        # --- End Fetch Target ---

        # --- Project Verification (same as is-sft endpoint) ---
        belongs_to_project = False
        stmt_check_response = (
            select(models.CompletionResponse.id)
            .join(models.CompletionsRequest, models.CompletionResponse.completion_request_id == models.CompletionsRequest.id)
            .where(models.CompletionResponse.annotation_target_id == annotation_target_id)
            .where(models.CompletionsRequest.project_id == project_id)
            .limit(1)
        )
        result_resp = await db.execute(stmt_check_response)
        if result_resp.scalar_one_or_none() is not None:
            belongs_to_project = True

        if not belongs_to_project:
            stmt_check_alt = (
                select(models.CompletionAlternative.id)
                .where(models.CompletionAlternative.annotation_target_id == annotation_target_id)
                .where(models.CompletionAlternative.project_id == project_id)
                .limit(1)
            )
            result_alt = await db.execute(stmt_check_alt)
            if result_alt.scalar_one_or_none() is not None:
                belongs_to_project = True

        if not belongs_to_project:
            logger.warning(f"Annotation target {annotation_target_id} not found in project {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation target not found in this project."
            )
        # --- End Project Verification ---

        # Determine if this is a DPO negative example using the new function
        is_dpo_neg = is_dpo_negative_example(target, active_schema=active_schema_content, threshold=threshold)
        logger.info(f"Annotation target {annotation_target_id}: is_dpo_negative={is_dpo_neg} (threshold={threshold}, schema_checked={active_schema_content is not None})")

        return is_dpo_neg

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error checking if annotation target {annotation_target_id} is a DPO negative example: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to determine DPO negative status due to an internal error."
        )

# ... rest of the router code ...

# ... after get_sft_request_count endpoint ...

@router.get(
    "/{project_id}/dpo-ready-count",
    response_model=DpoReadyCountResponse,
    summary="Get the count of requests ready for DPO."
)
async def get_dpo_ready_count(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
    sft_threshold: float = Query(0.75, description="Minimum average reward for SFT examples."),
    dpo_negative_threshold: float = Query(0.25, description="Maximum average reward for DPO negative examples.")
):
    """
    Calculates and returns the number of unique CompletionsRequests
    within the project that have at least one SFT example AND at least one DPO negative example.
    """
    logger.info(f"Calculating DPO ready count for project {project_id} for user {membership.user_id}")

    try:
        # --- Fetch Active Schema Once ---
        active_schema_content: Optional[Dict[str, Any]] = None
        try:
            # (Same schema fetching logic as in get_requests_summary)
            stmt_schema = (
                select(models.ProjectJsonSchema)
                .where(models.ProjectJsonSchema.project_id == project_id)
                .where(models.ProjectJsonSchema.is_active == True)
                .order_by(models.ProjectJsonSchema.created_at.desc())
            )
            result_schema = await db.execute(stmt_schema)
            active_schema_obj = result_schema.scalars().first()
            if active_schema_obj:
                active_schema_content = active_schema_obj.schema_content
                logger.debug(f"Found active schema {active_schema_obj.id} for DPO ready count.")
            else:
                logger.debug(f"No active schema found for project {project_id}. DPO ready count will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema for DPO ready count (project {project_id}): {schema_exc}", exc_info=True)
        # --- End Fetch Active Schema ---

        # --- Query to fetch requests and necessary related data for DPO check ---
        # This query needs to load relationships needed by is_dpo_ready
        stmt_requests = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.project_id == project_id)
            .options(
                # Load relationships needed by is_dpo_ready -> is_sft_example / is_dpo_negative_example
                selectinload(models.CompletionsRequest.completion_response)
                .selectinload(models.CompletionResponse.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                ),
                selectinload(models.CompletionsRequest.alternatives)
                .selectinload(models.CompletionAlternative.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                )
            )
            # No ordering needed for just counting
        )
        # --- End Query ---

        result = await db.execute(stmt_requests)
        # Use unique() because joinedload can cause duplicate parent objects
        requests = result.scalars().unique().all()

        dpo_ready_request_count = 0
        for req in requests:
            # Call is_dpo_ready with the request and thresholds
            if is_dpo_ready(
                request=req,
                active_schema=active_schema_content,
                sft_threshold=sft_threshold,
                dpo_negative_threshold=dpo_negative_threshold
            ):
                dpo_ready_request_count += 1
                # No need to break, is_dpo_ready already checks the whole request

        logger.info(f"Found {dpo_ready_request_count} DPO-ready requests for project {project_id}")
        return DpoReadyCountResponse(dpo_ready_count=dpo_ready_request_count)

    except Exception as e:
        logger.exception(f"Error calculating DPO ready count for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate DPO ready count due to an internal error."
        )

@router.get(
    "/{project_id}/sft-request-count",
    response_model=SftRequestCountResponse,
    summary="Get the count of requests ready for SFT."
)
async def get_sft_request_count(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
    sft_threshold: float = 0.75
):
    """
    Calculates and returns the number of unique CompletionsRequests
    within the project that have at least one associated AnnotationTarget
    meeting the SFT criteria (reward threshold and schema compliance if applicable).
    """
    logger.info(f"Calculating SFT request count for project {project_id} for user {membership.user_id}")

    try:
        # --- Fetch Active Schema Once ---
        active_schema_content: Optional[Dict[str, Any]] = None
        try:
            # (Same schema fetching logic as in get_requests_summary)
            stmt_schema = (
                select(models.ProjectJsonSchema)
                .where(models.ProjectJsonSchema.project_id == project_id)
                .where(models.ProjectJsonSchema.is_active == True)
                .order_by(models.ProjectJsonSchema.created_at.desc())
            )
            result_schema = await db.execute(stmt_schema)
            active_schema_obj = result_schema.scalars().first()
            if active_schema_obj:
                active_schema_content = active_schema_obj.schema_content
                logger.debug(f"Found active schema {active_schema_obj.id} for SFT count.")
            else:
                logger.debug(f"No active schema found for project {project_id}. SFT count will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema for SFT count (project {project_id}): {schema_exc}", exc_info=True)
        # --- End Fetch Active Schema ---

        # --- Query to fetch requests and necessary related data for SFT check ---
        # This query needs to be efficient for counting, loading only what's needed by is_sft_example
        stmt_requests = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.project_id == project_id)
            .options(
                # Load relationships needed by is_sft_example, using joinedload for efficiency
                selectinload(models.CompletionsRequest.completion_response)
                .selectinload(models.CompletionResponse.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                ),
                selectinload(models.CompletionsRequest.alternatives)
                .selectinload(models.CompletionAlternative.annotation_target)
                .options(
                    selectinload(models.AnnotationTarget.annotations),
                    joinedload(models.AnnotationTarget.completion_response, innerjoin=False),
                    joinedload(models.AnnotationTarget.completion_alternative, innerjoin=False)
                )
            )
            # No ordering needed for just counting
        )
        # --- End Query ---

        result = await db.execute(stmt_requests)
        # Use unique() because joinedload can cause duplicate parent objects
        requests = result.scalars().unique().all()

        sft_ready_request_count = 0
        for req in requests:
            targets_to_check: List[models.AnnotationTarget] = []
            if req.completion_response and req.completion_response.annotation_target:
                targets_to_check.append(req.completion_response.annotation_target)
            if req.alternatives:
                for alt in req.alternatives:
                    if alt.annotation_target:
                        targets_to_check.append(alt.annotation_target)

            for target in targets_to_check:
                # Call is_sft_example with target and schema
                if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                    sft_ready_request_count += 1
                    break # Found one SFT example for this request, move to the next request

        logger.info(f"Found {sft_ready_request_count} SFT-ready requests for project {project_id}")
        return SftRequestCountResponse(sft_request_count=sft_ready_request_count)

    except Exception as e:
        logger.exception(f"Error calculating SFT request count for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate SFT request count due to an internal error."
        )
    
@router.get(
    "/{project_id}/sft-dataset.jsonl",
    summary="Generate an SFT dataset (JSON Lines) for the project",
    response_class=Response # Use FastAPI's Response class directly
)
async def download_sft_dataset_jsonl(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    sft_threshold: float = Query(0.75, description="The minimum average reward threshold for SFT examples."),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Generates a dataset suitable for Supervised Fine-Tuning (SFT) in JSON Lines format.

    Each line in the response body is a JSON object representing one conversation
    that meets the SFT criteria (based on reward threshold and schema compliance if applicable).
    """
    logger.info(f"Generating SFT dataset (JSONL) for project {project_id} by user {membership.user_id}")

    try:
        sft_data: List[SftConversationSchema] = await _generate_project_sft_data(
            project_id=project_id,
            db=db,
            sft_threshold=sft_threshold
        )

        if not sft_data:
            logger.info(f"No SFT data generated for project {project_id}. Returning empty response.")
            return Response(content="", media_type="application/jsonl", status_code=status.HTTP_200_OK) # Return empty 200

        # Convert list of Pydantic objects to JSONL string
        # Use exclude_none=True if you want to omit fields like 'weight' if they are None
        jsonl_content = "\n".join([conv.model_dump_json(exclude_none=True) for conv in sft_data])

        # Add a final newline character, common for JSONL files
        jsonl_content += "\n"

        # Set headers for file download
        headers = {
            'Content-Disposition': f'attachment; filename="sft_dataset_{project_id}.jsonl"'
        }

        return Response(content=jsonl_content, media_type="application/jsonl", headers=headers)

    except Exception as e:
        logger.exception(f"Error generating SFT JSONL dataset for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SFT dataset due to an internal error."
        )

@router.get(
    "/{project_id}/dpo-dataset.jsonl",
    summary="Generate a DPO dataset (JSON Lines) for the project",
    response_class=Response 
)
async def download_dpo_dataset_jsonl(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    sft_threshold: float = Query(0.75, description="Minimum average reward for SFT examples (preferred)."),
    dpo_negative_threshold: float = Query(0.25, description="Maximum average reward for DPO negative examples (non-preferred)."),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Generates a dataset suitable for Direct Preference Optimization (DPO) in JSON Lines format.

    Each line in the response body is a JSON object representing one DPO example,
    containing an input, a preferred assistant response, and a non-preferred assistant response.
    These are derived from requests that have at least one SFT-qualifying response and
    at least one DPO-negative-qualifying response associated with them.
    """
    logger.info(f"Generating DPO dataset (JSONL) for project {project_id} by user {membership.user_id}")

    try:
        dpo_data: List[DpoExampleSchema] = await _generate_project_dpo_data(
            project_id=project_id,
            db=db,
            sft_threshold=sft_threshold,
            dpo_negative_threshold=dpo_negative_threshold
        )

        if not dpo_data:
            logger.info(f"No DPO data generated for project {project_id} with current thresholds. Returning empty response.")
            return Response(content="", media_type="application/jsonl", status_code=status.HTTP_200_OK)

        # Convert list of Pydantic objects to JSONL string
        jsonl_content = "\n".join([example.model_dump_json(exclude_none=True) for example in dpo_data])
        # Add a final newline character, common for JSONL files
        jsonl_content += "\n"

        # Set headers for file download
        headers = {
            'Content-Disposition': f'attachment; filename="dpo_dataset_{project_id}.jsonl"'
        }

        return Response(content=jsonl_content, media_type="application/jsonl", headers=headers)

    except Exception as e:
        logger.exception(f"Error generating DPO JSONL dataset for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate DPO dataset due to an internal error."
        )

@router.delete(
    "/{project_id}/schemas/active",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate the currently active JSON schema for the project."
)
async def deactivate_current_project_schema(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
):
    """
    Deactivates the most recently created 'is_active'=True JSON schema for the project.
    If no active schema exists, this operation will return a 404.
    """
    logger.info(f"Attempting to deactivate active schema for project {project_id} by user {membership.user_id}")

    # Find the current active schema
    stmt_find_active = (
        select(models.ProjectJsonSchema)
        .where(models.ProjectJsonSchema.project_id == project_id)
        .where(models.ProjectJsonSchema.is_active == True)
        .order_by(models.ProjectJsonSchema.created_at.desc())
    )
    result_active = await db.execute(stmt_find_active)
    active_schema = result_active.scalars().first()

    if not active_schema:
        logger.info(f"No active schema found for project {project_id} to deactivate.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active schema found for this project to deactivate."
        )

    try:
        active_schema.is_active = False
        db.add(active_schema) # Mark the instance as changed
        await db.commit()
        logger.info(f"Successfully deactivated schema {active_schema.id} for project {project_id}")
        # FastAPI will return 204 No Content based on the decorator
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error deactivating schema {active_schema.id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate schema due to an internal error."
        )
