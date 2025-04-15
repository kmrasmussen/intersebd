from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import os
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from config import settings

# imports from solutions
from config import settings

oauth = OAuth()
oauth.register(
  name='google',
  server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
  client_id=settings.google_client_id,
  client_secret=settings.google_client_secret,
  client_kwargs={
    'scope': 'openid email profile',
    'redirect_uri': settings.google_redirect_uri,
  })

class UserInfo(BaseModel):
  sub: str
  email: str
  name: Optional[str] = None

class LoginStatusResponse(BaseModel):
  is_logged_in: bool
  user_info: Optional[UserInfo] = None

router = APIRouter(
  prefix="/auth",
  tags=["authentication"],
)

async def get_current_user(request : Request) -> Optional[UserInfo]:
  user_info_dict = request.session.get('user')
  if user_info_dict:
    try:

      return UserInfo(**user_info_dict)
    except Exception:
      request.session.pop('user', None)
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        details="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
      )
  raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
  )

@router.get("/login/google")
async def login_via_google(request: Request):
  redirect_uri = request.url_for('auth_google_callback')
  print("Generate Redirect URI for Google: ", redirect_uri)
  return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/login/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request):
  try:
    token = await oauth.google.authorize_access_token(request)
    print('got token back from google', token)
  except Exception as e:
    print("Error authorizaing access token from Google: ", e)
    raise HTTPException(status_code=400, detail="Authorization failed from Google: {e}")

  user_info_google = token.get('userinfo')
  if not user_info_google:
    print('Could not fetch user info from token from Google callback')
    raise HTTPException(status_code=400, detail="Could not fetch user info from token")
  
  try:
    user = UserInfo(**user_info_google)
  except Exception as e:
    print('Validating user info from Google against Pydantic model failed: ', e)
    raise HTTPException(status_code=400, detail="Invalid user info from Google")

  request.session['user'] = user.model_dump()

  print(f'Successfully authenticated user: {user}')
  print('google callback, user was successfully authenticated', {
    "message": "Successfully authenticated",
    "user_info": user.model_dump()
  })
  return RedirectResponse(url=settings.frontend_base_url)

@router.get("/login_status", response_model=LoginStatusResponse)
async def check_login_status(current_user: Optional[UserInfo] = Depends(get_current_user)):
  if current_user:
    return LoginStatusResponse(is_logged_in=True, user_info=current_user)
  else:
    return LoginStatusResponse(is_logged_in=False)
  
@router.get("/logout")
async def logout(request : Request):
  request.session.pop('user', None)
  print('successfully logged out user')
  return RedirectResponse(url=settings.frontend_base_url)