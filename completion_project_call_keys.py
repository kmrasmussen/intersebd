from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import uuid
from typing import Optional, List # Added List for potential future use
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
from database import get_db
from auth import get_current_user, verify_project_membership # Import the new dependency
# Import the KeySchema from completion_projects
from completion_projects import KeySchema # Assuming KeySchema is defined here

router = APIRouter(
    prefix="/completion-project-call-keys",
    tags=["completion-project-call-keys"],
    # No global dependencies here, apply them per-route or use the membership dependency
)

# --- Endpoint to get *one* active call key for a specific project ---
@router.get("/{project_id}/some-call-key", response_model=KeySchema)
async def get_some_active_call_key(
    project_id: uuid.UUID, # Get project_id from path
    db: AsyncSession = Depends(get_db),
    # Use the dependency to verify membership and get current_user implicitly
    membership: models.ProjectMembership = Depends(verify_project_membership)
):
    """
    Retrieves a single active API call key for the specified project,
    ensuring the current user is a member of the project.
    """
    # If we reach here, verify_project_membership succeeded:
    # - User is authenticated (via get_current_user within verify_project_membership)
    # - User is a member of the project_id passed in the path

    # Fetch *one* active key for this authorized project
    stmt_key = select(models.CompletionProjectCallKeys).filter(
        models.CompletionProjectCallKeys.project_id == project_id, # Use project_id from path
        models.CompletionProjectCallKeys.is_active == True
    ).limit(1) # Ensure we only get one

    result_key = await db.execute(stmt_key)
    active_key = result_key.scalars().first()

    if not active_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active call keys found for project {project_id}."
        )

    # Return the found key using the KeySchema
    return active_key

# --- Placeholder for other key-related endpoints ---
# Example: List all keys for a project
# @router.get("/{project_id}", response_model=List[KeySchema])
# async def list_project_keys(
#     project_id: uuid.UUID,
#     db: AsyncSession = Depends(get_db),
#     membership: models.ProjectMembership = Depends(verify_project_membership)
# ):
#     # Check membership.role if needed for listing
#     stmt = select(models.CompletionProjectCallKeys).filter(models.CompletionProjectCallKeys.project_id == project_id)
#     result = await db.execute(stmt)
#     keys = result.scalars().all()
#     return keys

# Example: Create a new key for a project
# @router.post("/{project_id}", response_model=KeySchema, status_code=status.HTTP_201_CREATED)
# async def create_project_key(
#     project_id: uuid.UUID,
#     # Optional: Add request body for key details (e.g., name)
#     db: AsyncSession = Depends(get_db),
#     membership: models.ProjectMembership = Depends(verify_project_membership)
# ):
#     # IMPORTANT: Check membership.role here - e.g., only 'owner' or 'editor' can create keys
#     if membership.role not in ['owner', 'editor']:
#          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to create keys.")
#     # ... logic to create new key ...