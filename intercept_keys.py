import secrets
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select

from database import get_db
from models import InterceptKey
from auth import get_current_user, UserInfo

class NewInterceptKeyResponse(BaseModel):
  intercept_key: str
  message: str

class InterceptKeyDetails(BaseModel):
  intercept_key: str
  created_at: datetime
  is_valid: bool

  class Config:
    from_attributes = True

class ListInterceptKeysResponse(BaseModel):
  keys: List[InterceptKeyDetails]

router = APIRouter(
  prefix='/intercept-keys',
  tags=["Intercept keys"],
  dependencies=[Depends(get_current_user)]
)

@router.post('/',
             response_model=NewInterceptKeyResponse,
             status_code=status.HTTP_201_CREATED)
async def create_new_intercept_key(
  current_user: UserInfo = Depends(get_current_user),
  session: AsyncSession = Depends(get_db)
):

  new_key_value = secrets.token_urlsafe(32)

  new_intercept_key_db_row = InterceptKey(
    user_id=current_user.sub,
    intercept_key=new_key_value,
    is_valid=True
  )

  try:
    session.add(new_intercept_key_db_row)
    await session.commit()
  except Exception as e:
    await session.rollback()
    print(f"Error saving new intercept key: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="could not create intercept key row in db"
    )
  
  return NewInterceptKeyResponse(
    intercept_key=new_key_value,
    message="New intercept key created successfully"
  )

@router.get('/', response_model=ListInterceptKeysResponse)
async def list_intercept_keys(
  current_user: UserInfo = Depends(get_current_user),
  session: AsyncSession = Depends(get_db)
):
  stmt = select(InterceptKey).where(InterceptKey.user_id == current_user.sub).order_by(InterceptKey.created_at.desc())
  results = await session.execute(stmt)
  user_keys = results.scalars().all()

  return ListInterceptKeysResponse(keys=user_keys)