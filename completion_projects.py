from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

import models
from database import get_db
from auth import get_current_user
from provider_keys import _fetch_new_openrouter_key_data

logger = logging.getLogger(__name__)

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

# --- Endpoint to Create/Get Default Project ---

@router.post("/default", response_model=DefaultProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_default_project(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user)
):
    if not current_user:
        logger.warning("create_or_get_default_project: No authenticated user found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated or identified"
        )

    user_to_use = current_user
    logger.info(f"create_or_get_default_project: Proceeding for user {user_to_use.id}")

    # --- Check if Default Project Exists ---
    stmt_proj = select(models.CompletionProject).filter(
        models.CompletionProject.creator_id == user_to_use.id,
        models.CompletionProject.name == "Default Project"
    )
    result_proj = await db.execute(stmt_proj)
    existing_default = result_proj.scalars().first()

    if existing_default:
        logger.info(f"Default project {existing_default.id} already exists for user {user_to_use.id}")
        stmt_mem_check = select(models.ProjectMembership).filter(
            models.ProjectMembership.project_id == existing_default.id,
            models.ProjectMembership.user_id == user_to_use.id
        ).limit(1)
        result_mem_check = await db.execute(stmt_mem_check)
        existing_membership = result_mem_check.scalars().first()
        if not existing_membership:
            logger.warning(f"WARN: Default project {existing_default.id} exists but owner membership missing. Adding...")

        stmt_key = select(models.CompletionProjectCallKeys).filter(
            models.CompletionProjectCallKeys.project_id == existing_default.id
        ).limit(1)
        result_key = await db.execute(stmt_key)
        existing_key = result_key.scalars().first()

        return DefaultProjectResponse(
            project=ProjectSchema.model_validate(existing_default),
            key=KeySchema.model_validate(existing_key) if existing_key else None
        )

    # --- Create Default Project, Membership, Call Key, and Provider Key ---
    logger.info(f"Creating new default project for user {user_to_use.id}")

    new_project = models.CompletionProject(
        name="Default Project",
        description="Your first project.",
        creator_id=user_to_use.id
    )

    owner_membership = models.ProjectMembership(
        user=user_to_use,
        project=new_project,
        role='owner'
    )

    call_key_value = f"sk_{uuid.uuid4().hex}"
    new_call_key = models.CompletionProjectCallKeys(
        project=new_project,
        key=call_key_value
    )

    try:
        or_key_data = await _fetch_new_openrouter_key_data()
    except HTTPException as http_exc:
        logger.error(f"Failed to fetch OpenRouter key data: {http_exc.detail} (Status: {http_exc.status_code})")
        raise HTTPException(status_code=http_exc.status_code, detail=f"Failed to provision necessary backend key: {http_exc.detail}")
    except Exception as e:
        logger.exception("Unexpected error fetching OpenRouter key data.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected internal error during key provisioning.")

    new_or_key = models.OpenRouterGuestKey(
        user=user_to_use,
        completion_project_call_key=new_call_key,
        **or_key_data
    )

    try:
        db.add_all([new_project, owner_membership, new_call_key, new_or_key])
        await db.commit()

        await db.refresh(new_project)
        await db.refresh(new_call_key)
        await db.refresh(new_or_key)

        logger.info(f"Created project {new_project.id}, membership, call key {new_call_key.id}, and linked OR key {new_or_key.id}")

    except (SQLAlchemyError, IntegrityError) as e:
        await db.rollback()
        logger.error(f"Database error creating default project structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save default project structure: {e}"
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error during database commit/refresh for default project.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected internal error saving project data."
        )

    return DefaultProjectResponse(
        project=ProjectSchema.model_validate(new_project),
        key=KeySchema.model_validate(new_call_key)
    )

# --- Other project endpoints ---

@router.get("", response_model=List[ProjectSchema])
async def get_user_projects(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view projects",
        )
    stmt = select(models.CompletionProject).join(models.ProjectMembership).filter(
        models.ProjectMembership.user_id == current_user.id
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return projects

@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project_by_id(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    stmt = select(models.CompletionProject).join(models.ProjectMembership).filter(
        models.CompletionProject.id == project_id,
        models.ProjectMembership.user_id == current_user.id
    )
    result = await db.execute(stmt)
    project = result.scalars().first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found or access denied",
        )
    return project
