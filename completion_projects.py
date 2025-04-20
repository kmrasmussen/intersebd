from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
from database import get_db
from auth import get_current_user, GUEST_USER_ID_COOKIE

# --- Pydantic Schemas ---

class ProjectSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    creator_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

class KeySchema(BaseModel):
    id: uuid.UUID
    key: str
    project_id: uuid.UUID
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class DefaultProjectResponse(BaseModel):
    project: ProjectSchema
    key: Optional[KeySchema] = None

class DefaultProjectRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None

# --- Router ---

router = APIRouter(
    prefix="/completion-projects",
    tags=["completion-projects"],
)

# --- Endpoint to Create Default Project ---

@router.post("/default", response_model=DefaultProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_default_project(
    request_body: Optional[DefaultProjectRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user_from_cookie: Optional[models.User] = Depends(get_current_user)
):
    user_to_use: Optional[models.User] = None
    user_id_to_query: Optional[uuid.UUID] = None

    # Priority 1: User ID from request body (for immediate guest creation)
    if request_body and request_body.user_id:
        print(f"create_default_project: Received user_id in request body: {request_body.user_id}")
        user_id_to_query = request_body.user_id
    # Priority 2: User from cookie/session dependency
    elif current_user_from_cookie:
        print(f"create_default_project: Using user from cookie/session: {current_user_from_cookie.id}")
        user_to_use = current_user_from_cookie
        user_id_to_query = current_user_from_cookie.id
    else:
        # No user ID in body and no user from cookie/session
        print("create_default_project: No user_id in body and no user from cookie/session.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated or identified"
        )

    # If we only have the ID (from body), fetch the user object
    if not user_to_use and user_id_to_query:
        stmt_user = select(models.User).filter(models.User.id == user_id_to_query)
        result_user = await db.execute(stmt_user)
        user_to_use = result_user.scalars().first()
        if not user_to_use:
             print(f"create_default_project: User ID {user_id_to_query} from body not found in DB.")
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User specified in request not found"
            )
        print(f"create_default_project: Fetched user from DB using ID from body: {user_to_use.id}")

    # --- Proceed with existing logic using user_to_use ---
    print(f"create_default_project: Proceeding for user {user_to_use.id}")

    # Check if Default Project Exists
    stmt_proj = select(models.CompletionProject).filter(
        models.CompletionProject.creator_id == user_to_use.id,
        models.CompletionProject.name == "Default Project"
    )
    result_proj = await db.execute(stmt_proj)
    existing_default = result_proj.scalars().first()

    if existing_default:
        print(f"Default project {existing_default.id} already exists for user {user_to_use.id}")
        stmt_key = select(models.CompletionProjectCallKeys).filter(
            models.CompletionProjectCallKeys.project_id == existing_default.id
        )
        result_key = await db.execute(stmt_key)
        existing_key = result_key.scalars().first()
        return DefaultProjectResponse(
            project=ProjectSchema.model_validate(existing_default),
            key=KeySchema.model_validate(existing_key) if existing_key else None
        )

    # Create Default Project
    print(f"Creating new default project for user {user_to_use.id}")
    new_project = models.CompletionProject(
        name="Default Project",
        description="Your first project.",
        creator_id=user_to_use.id
    )
    db.add(new_project)
    try:
        await db.commit()
        await db.refresh(new_project)
        print(f"Created project {new_project.id}")
    except SQLAlchemyError as e:
        await db.rollback()
        print(f"Error creating default project DB commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create default project: {e}"
        )

    # Create Default Key
    key_value = f"sk_{uuid.uuid4().hex}"
    new_key = models.CompletionProjectCallKeys(
        project_id=new_project.id,
        key=key_value
    )
    db.add(new_key)
    try:
        await db.commit()
        await db.refresh(new_key)
        print(f"Created default key {new_key.id} for project {new_project.id}")
    except SQLAlchemyError as e:
        await db.rollback()
        print(f"Error creating default key DB commit: {e}")
        new_key = None

    return DefaultProjectResponse(
        project=ProjectSchema.model_validate(new_project),
        key=KeySchema.model_validate(new_key) if new_key else None
    )

# --- Add other project endpoints here ---

# Example: Get all projects for the current user
@router.get("", response_model=List[ProjectSchema])
def get_user_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view projects",
        )
    projects = db.query(models.CompletionProject).filter(models.CompletionProject.creator_id == current_user.id).all()
    return projects

# Example: Get a specific project by ID (ensure user has access)
@router.get("/{project_id}", response_model=ProjectSchema)
def get_project_by_id(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    project = db.query(models.CompletionProject).filter(
        models.CompletionProject.id == project_id,
        models.CompletionProject.creator_id == current_user.id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found or access denied",
        )
    return project
