from fastapi import APIRouter, Path, HTTPException, Depends, status, Body, Query
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any, Union
import uuid
import logging
import json
from datetime import datetime, timezone

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
                conversation = SftConversationSchema(messages=base_messages + [assistant_message])
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

# --- Router ---

router = APIRouter(
    prefix="/mock-next",
    tags=["Mock Data for Next.js Frontend"],
)

@router.get("/{project_id}/requests-summary", response_model=List[MockRequestSummary])
async def get_requests_summary(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership),
    sft_threshold: float = 0.75
):
    """
    Retrieves a summary of completion requests for the specified project.
    Calculates SFT status based on annotations and schema compliance.
    Requires the user to be a member of the project.
    """
    logger.info(f"Fetching requests summary for project ID: {project_id} for user {membership.user_id}")

    try:
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
                logger.debug(f"Found active schema {active_schema_obj.id} for request summary SFT checks.")
            else:
                logger.debug(f"No active schema found for project {project_id}. SFT checks will only use reward.")
        except Exception as schema_exc:
            logger.error(f"Error fetching active schema for request summary (project {project_id}): {schema_exc}", exc_info=True)
            # Continue without schema validation if fetching fails
        # --- End Fetch Active Schema ---

        # --- Query with outerjoin reinstated for sorting ---
        stmt_requests = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.project_id == project_id)
            # Add the outerjoin back specifically for the ORDER BY clause
            .outerjoin(models.CompletionResponse, models.CompletionsRequest.completion_response)
            .options(
                # Keep the selectinload/joinedload structure for data loading
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
                # This should now work because of the outerjoin above
                models.CompletionResponse.created.desc().nullslast(),
                models.CompletionsRequest.id.desc()
            )
        )
        # --- End Query ---

        result = await db.execute(stmt_requests)
        # Keep unique() as joinedload might still cause duplicates
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
                     pass # Keep N/A if no valid timestamps

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

            targets_to_check: List[models.AnnotationTarget] = []
            if req.completion_response and req.completion_response.annotation_target:
                targets_to_check.append(req.completion_response.annotation_target)
            if req.alternatives:
                for alt in req.alternatives:
                    if alt.annotation_target:
                        targets_to_check.append(alt.annotation_target)

            total_responses = len(targets_to_check)

            for target in targets_to_check:
                if target.annotations:
                    annotated_responses_count += 1
                    # Call updated is_sft_example with target and schema
                    if is_sft_example(target, active_schema=active_schema_content, threshold=sft_threshold):
                        request_sft_status = "complete"
                        break # Found one SFT example

            summary = MockRequestSummary(
                id=req_id_str,
                name=name,
                question=question,
                totalResponses=total_responses,
                annotatedResponses=annotated_responses_count,
                timestamp=timestamp_str,
                sftStatus=request_sft_status,
                dpoStatus="none",
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