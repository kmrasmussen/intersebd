from fastapi import APIRouter, Request, Depends, HTTPException, status, Response  # Added Response
from pydantic import BaseModel, Field  # Added Field
from typing import Optional
import os
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession  # Changed to AsyncSession
from sqlalchemy.future import select  # Use select for async queries
from database import get_db  # Import your DB session getter
import models  # Import your models
import uuid  # Import uuid
from datetime import datetime  # Import datetime
from sqlalchemy.exc import SQLAlchemyError  # Import SQLAlchemyError for broader DB exceptions

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

# Pydantic schema for User model (adjust fields as needed)
class UserSchema(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    google_id: Optional[str] = None
    auth_provider: Optional[str] = None
    name: Optional[str] = None
    is_active: bool
    created_at: datetime  # Assuming datetime is imported or use appropriate type

    class Config:
        from_attributes = True  # Use orm_mode for older Pydantic versions

class UserInfo(BaseModel):
    sub: str
    email: str
    name: Optional[str] = None

# Update LoginStatusResponse to include is_guest
class LoginStatusResponse(BaseModel):
    is_logged_in: bool  # True only if authenticated via session (Google)
    is_guest: bool      # True if identified via guest cookie
    user_info: Optional[UserSchema] = None  # Contains info for logged-in or guest

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

# --- Guest Cookie Name ---
GUEST_USER_ID_COOKIE = "guest_user_id"

# --- Async get_current_user ---
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[models.User]: # Changed to async def, type hint AsyncSession
    print(f"get_current_user: All cookies: {request.cookies}") # DEBUG
    guest_user_id_str = request.cookies.get(GUEST_USER_ID_COOKIE)
    print(f"get_current_user: Found guest cookie value: {guest_user_id_str}") # DEBUG

    if guest_user_id_str:
        try:
            guest_user_id = uuid.UUID(guest_user_id_str)
            # Use async query with select
            stmt = select(models.User).filter(models.User.id == guest_user_id)
            result = await db.execute(stmt)
            user = result.scalars().first() # Use scalars().first() for async result
            if user:
                print(f"get_current_user: Found guest user in DB: {user.id}") # DEBUG
                return user
            else:
                print(f"get_current_user: Guest user ID {guest_user_id} not found in DB.") # DEBUG
        except (ValueError, TypeError) as e:
            print(f"get_current_user: Invalid guest user ID format in cookie: {guest_user_id_str}, Error: {e}") # DEBUG
        except Exception as e:
             print(f"get_current_user: Database error looking up guest user: {e}") # DEBUG

    # Check for session-based user (Google Login) - Assuming synchronous session handling for now
    # If session middleware is also async, this part might need adjustment too
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            # Use async query
            stmt = select(models.User).filter(models.User.id == user_uuid)
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user:
                 print(f"get_current_user: Found session user in DB: {user.id}") # DEBUG
                 return user
            else:
                 print(f"get_current_user: Session user ID {user_uuid} not found in DB.") # DEBUG
        except (ValueError, TypeError) as e:
            print(f"get_current_user: Invalid user ID format in session: {user_id}, Error: {e}") # DEBUG
        except Exception as e:
             print(f"get_current_user: Database error looking up session user: {e}") # DEBUG

    print("get_current_user: No valid user found, returning None.") # DEBUG
    return None

@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_google_callback')
    print("Generate Redirect URI for Google: ", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/login/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request, response: Response, db: AsyncSession = Depends(get_db)): # Changed to AsyncSession
    try:
        token = await oauth.google.authorize_access_token(request)
        print('got token back from google', token)
    except Exception as e:
        print(f"Error authorizing access token from Google: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Authorization failed from Google: {e}")

    user_info_google = token.get('userinfo')
    if not user_info_google:
        print('Could not fetch user info from token from Google callback')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch user info from token")

    # Use the UserInfo model to validate and extract Google data
    try:
        google_user_data = UserInfo(**user_info_google)
        google_id = google_user_data.sub
        email = google_user_data.email
        name = google_user_data.name
    except Exception as e:
        print('Validating user info from Google against Pydantic model failed: ', e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user info from Google")

    if not google_id or not email:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required user info (sub, email) from Google")

    # --- Simplified Database Logic ---
    # 1. Check if user exists with this Google ID
    stmt = select(models.User).filter(models.User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user:
        # --- Case 1: Existing Registered User Found ---
        print(f"Found existing registered user by Google ID: {user.id}")
        # Optionally update email/name if changed in Google
        needs_update = False
        if user.email != email:
            user.email = email
            needs_update = True
        if user.name != name:
            user.name = name
            needs_update = True
        if needs_update:
            await db.commit()
            await db.refresh(user)

    else:
        # --- Case 2: No User Found by Google ID - Check for email conflict and Create New ---
        print(f"No user found for Google ID {google_id}. Checking email {email} and creating new user.")
        # Check if another user already exists with this email (conflict)
        stmt = select(models.User).filter(models.User.email == email)
        result = await db.execute(stmt)
        existing_email_user = result.scalars().first()
        if existing_email_user:
             # If email exists but google_id didn't match, it's a conflict
             raise HTTPException(
                 status_code=status.HTTP_409_CONFLICT,
                 detail=f"An account with email '{email}' already exists but is not linked to this Google account.")

        # Create a brand new user record
        user = models.User(
            google_id=google_id,
            email=email,
            name=name,
            auth_provider='google' # Mark as registered via Google
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created new registered user: {user.id}")

    # --- Store User ID (UUID as string) in session ---
    # Ensure session middleware is configured correctly in your main FastAPI app
    request.session['user_id'] = str(user.id)

    # Clear any potential guest cookie now that they are logged in
    response.delete_cookie(GUEST_USER_ID_COOKIE)

    print(f'Successfully authenticated user: {user.id} ({user.email})')

    # Redirect to frontend base URL - frontend will handle routing based on login status
    # Need to return the response object that has the cookie deletion set
    redirect_resp = RedirectResponse(url=settings.frontend_base_url)
    # Apply cookie deletion to the redirect response
    redirect_resp.delete_cookie(GUEST_USER_ID_COOKIE)
    return redirect_resp

@router.get("/login_status", response_model=LoginStatusResponse)
async def check_login_status(current_user: Optional[models.User] = Depends(get_current_user)):
    if current_user:
        user_schema = UserSchema.from_orm(current_user)
        is_logged_in = current_user.auth_provider == 'google' # Check if it's a Google user
        is_guest = current_user.auth_provider is None      # Check if it's a guest user
        return LoginStatusResponse(is_logged_in=is_logged_in, is_guest=is_guest, user_info=user_schema)
    else:
        # No session user and no valid guest cookie found
        return LoginStatusResponse(is_logged_in=False, is_guest=False)

@router.get("/logout")
async def logout(request: Request, response: Response): # Keep response parameter
    request.session.pop('user_id', None) # Pop user_id from session
    # Also clear the guest cookie on explicit logout
    response.delete_cookie(GUEST_USER_ID_COOKIE)
    print('successfully logged out user (session/cookie cleared)')

    # --- CHANGE: Return simple success response instead of redirect ---
    # The frontend will handle the page reload/redirect
    # Returning the 'response' object ensures the delete_cookie header is sent.
    response.status_code = status.HTTP_200_OK # Explicitly set 200 OK
    return response

# --- Endpoint to Create Guest User ---
class GuestUserResponse(BaseModel):
    guest_user_id: uuid.UUID

@router.post("/users/guest", response_model=GuestUserResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_user(response: Response, db: AsyncSession = Depends(get_db)): # Changed to async def, type hint AsyncSession
    generated_id = uuid.uuid4()
    print(f"Explicitly generated UUID: {generated_id}")
    guest_user = models.User(id=generated_id, auth_provider=None)

    if not isinstance(guest_user.id, uuid.UUID) or guest_user.id != generated_id:
         print(f"Critical Error: guest_user.id could not be assigned. Value: {guest_user.id}")
         raise HTTPException(status_code=500, detail="Failed to assign generated guest user ID.")

    print(f"Attempting to create guest user with assigned ID: {guest_user.id}")
    try:
        db.add(guest_user)
        await db.commit() # Use await
        try:
            await db.refresh(guest_user) # Use await
        except SQLAlchemyError as refresh_exc:
            # Note: Refresh might behave differently or be less necessary with async sessions depending on config
            print(f"Warning: db.refresh failed after commit. Error: {refresh_exc}")
    except SQLAlchemyError as e:
        await db.rollback() # Use await
        print(f"Error committing guest user to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error creating guest user: {e}")

    if not isinstance(guest_user.id, uuid.UUID):
         print(f"Error: guest_user.id is not UUID after commit/refresh. Value: {guest_user.id}")
         raise HTTPException(status_code=500, detail="Failed to retrieve valid guest user ID.")

    print(f"Successfully created guest user: {guest_user.id}")

    cookie_value = str(guest_user.id)
    cookie_key = GUEST_USER_ID_COOKIE
    # Revert to Lax, remove Secure
    print(f"Setting cookie: Key='{cookie_key}', Value='{cookie_value}', HttpOnly=True, SameSite='Lax', Path='/'") # DEBUG
    response.set_cookie(
        key=cookie_key,
        value=cookie_value,
        httponly=True,
        samesite="lax", # <-- REVERT TO 'lax' (or omit, as Lax is default)
        # secure=True,  # <-- REMOVE secure=True
        max_age=60*60*24*365,
        path="/"
    )
    return GuestUserResponse(guest_user_id=guest_user.id)