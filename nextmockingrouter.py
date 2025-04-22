from fastapi import APIRouter, Path, HTTPException, Depends, status, Body
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any, Union
import uuid
import logging
import json
from datetime import datetime, timezone

# --- DB and Auth Imports ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from database import get_db
from auth import verify_project_membership, get_current_user
import models
from models import User

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

        # --- Use user_id instead of rater_id ---
        annotator_str = "Unknown"
        if ann.user_id:
            # Convert the UUID user_id to string for the 'by' field
            annotator_str = str(ann.user_id)
        # --- End change ---

        mapped.append(Annotation(
            reward=reward_int,
            by=annotator_str,             # <-- USE new variable
            at=format_timestamp(ann.timestamp)
        ))
    return mapped

def map_to_response_detail(
    response_obj: Union[models.CompletionResponse, models.CompletionAlternative],
    request_model: str
) -> ResponseDetail:
    """Maps CompletionResponse or CompletionAlternative to Pydantic ResponseDetail."""
    content = None
    created_ts = None
    db_annotations = None
    response_id = None
    annotation_target_id_str: Optional[str] = None

    if isinstance(response_obj, models.CompletionResponse):
        response_id = response_obj.id
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
    obeys_schema = None

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

# --- Router ---

router = APIRouter(
    prefix="/mock-next",
    tags=["Mock Data for Next.js Frontend"],
)

@router.get("/{project_id}/requests-summary", response_model=List[MockRequestSummary])
async def get_requests_summary(
    project_id: uuid.UUID = Path(..., description="The UUID of the project"),
    db: AsyncSession = Depends(get_db),
    membership: models.ProjectMembership = Depends(verify_project_membership)
):
    """
    Retrieves a summary of completion requests for the specified project,
    linked directly via project_id.
    Requires the user to be a member of the project.
    Annotation counts are currently mocked.
    """
    logger.info(f"Fetcing requests summary for project ID: {project_id} for user {membership.user_id}")

    try:
        stmt_requests = (
            select(models.CompletionsRequest)
            .where(models.CompletionsRequest.project_id == project_id)
            .options(
                selectinload(models.CompletionsRequest.completion_response),
                selectinload(models.CompletionsRequest.alternatives)
            )
            .outerjoin(models.CompletionResponse, models.CompletionsRequest.completion_response)
            .order_by(models.CompletionResponse.created.desc().nullslast(), models.CompletionsRequest.id.desc())
        )

        result = await db.execute(stmt_requests)
        requests = result.scalars().unique().all()

        if not requests:
            logger.info(f"No completion requests found for project {project_id}")
            return []

        summary_list: List[MockRequestSummary] = []
        for req in requests:
            req_id_str = str(req.id)

            timestamp_str = "N/A"
            if req.completion_response and req.completion_response.created:
                try:
                    ts_datetime = datetime.fromtimestamp(req.completion_response.created, tz=timezone.utc)
                    timestamp_str = ts_datetime.isoformat().replace("+00:00", "Z")
                except Exception as ts_exc:
                    logger.warning(f"Could not parse timestamp {req.completion_response.created} for request {req_id_str}: {ts_exc}")

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

            total_responses = 0
            if req.completion_response:
                total_responses += 1
            total_responses += len(req.alternatives or [])

            annotated_responses_count = 0

            summary = MockRequestSummary(
                id=req_id_str,
                name=name,
                question=question,
                totalResponses=total_responses,
                annotatedResponses=annotated_responses_count,
                timestamp=timestamp_str,
                sftStatus="none",
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
    Requires the user to be a member of the project.
    """
    logger.info(f"Fetching details for request ID: {request_id} in project {project_id} for user {membership.user_id}")

    try:
        stmt = (
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

        result = await db.execute(stmt)
        req = result.scalars().first()

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

        main_response_detail: Optional[ResponseDetail] = None
        if req.completion_response:
            try:
                main_response_detail = map_to_response_detail(req.completion_response, req.model or "Unknown")
            except Exception as map_err:
                logger.error(f"Error mapping main response for request {req_id_str}: {map_err}", exc_info=True)

        alternative_response_details: List[ResponseDetail] = []
        if req.alternatives:
            for alt in req.alternatives:
                try:
                    alt_detail = map_to_response_detail(alt, req.model or "Unknown")
                    alternative_response_details.append(alt_detail)
                except Exception as map_err:
                    logger.error(f"Error mapping alternative response {alt.id} for request {req_id_str}: {map_err}", exc_info=True)

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

# --- NEW: Create Annotation Endpoint ---
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

    # Fetch the AnnotationTarget AND eagerly load its annotations relationship
    stmt_target = (
        select(models.AnnotationTarget)
        .where(models.AnnotationTarget.id == annotation_target_id)
        .options(selectinload(models.AnnotationTarget.annotations)) # <-- ADD THIS EAGER LOAD
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
        await db.flush() # Get the ID for the new annotation

        # Now append should work without triggering a lazy load
        target.annotations.append(new_annotation)

        await db.commit()
        await db.refresh(new_annotation) # Refresh to get timestamp etc.
        logger.info(f"Successfully created annotation {new_annotation.id} for target {annotation_target_id}")

    except Exception as e:
        await db.rollback()
        logger.exception(f"Error creating or linking annotation for target {annotation_target_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save annotation due to an internal error."
        )

    # Prepare response manually
    response_data = AnnotationResponse(
        id=new_annotation.id,
        timestamp=new_annotation.timestamp,
        user_id=new_annotation.user_id,
        reward=new_annotation.reward,
        annotation_metadata=new_annotation.annotation_metadata,
        annotation_target_id=annotation_target_id
    )

    return response_data