from fastapi import APIRouter, Request, Depends, HTTPException, status, Response  # Added Response
from pydantic import BaseModel, Field  # Added Field
from typing import Optional
import os
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from config import settings
from sqlalchemy.orm import Session  # Import Session
from database import get_db  # Import your DB session getter
import models  # Import your models
import uuid  # Import uuid
from datetime import datetime  # Import datetime

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

# Modified get_current_user to also check for guest cookie
async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    user: Optional[models.User] = None
    user_id_str = request.session.get('user_id') # Get user_id (UUID string) from session

    # --- 1. Check for Session User (Logged-in) ---
    if user_id_str:
        try:
            user_id = uuid.UUID(user_id_str) # Convert string back to UUID
            user = db.query(models.User).filter(models.User.id == user_id).first()

            if not user:
                # Session user ID exists but user not found in DB (stale session?)
                request.session.pop('user_id', None) # Clear invalid session data
                print(f"Session user_id {user_id_str} not found in DB. Clearing session.")
            # Optional: Check if user is active
            # elif not user.is_active:
            #     request.session.pop('user_id', None)
            #     print(f"Session user {user.id} is inactive. Clearing session.")
            #     user = None # Treat inactive user as not logged in for this context

        except ValueError:
            # Invalid UUID format in session
            request.session.pop('user_id', None) # Clear invalid session data
            print(f"Invalid UUID format in session user_id: {user_id_str}. Clearing session.")
            user = None # Ensure user is None if session ID was invalid

    # --- 2. If No Session User, Check for Guest Cookie ---
    if user is None:
        guest_user_id_str = request.cookies.get(GUEST_USER_ID_COOKIE)
        if guest_user_id_str:
            try:
                guest_user_id = uuid.UUID(guest_user_id_str)
                # Find user by ID only if they are marked as a guest (auth_provider is None)
                guest_user = db.query(models.User).filter(
                    models.User.id == guest_user_id,
                    models.User.auth_provider == None
                ).first()

                if guest_user:
                    print(f"Identified guest user via cookie: {guest_user.id}")
                    user = guest_user # Set user to the found guest user
                # else: User ID in cookie doesn't match a guest user in DB (stale/invalid cookie?)
                #     No action needed here, user remains None

            except ValueError:
                # Invalid UUID format in cookie
                print(f"Invalid UUID format in guest cookie: {guest_user_id_str}")
                # Optionally delete the invalid cookie? Might be aggressive.
                # response.delete_cookie(GUEST_USER_ID_COOKIE) # Need Response object here

    # --- 3. Return Found User (Logged-in or Guest) or None ---
    if user:
        print(f"get_current_user returning user: {user.id} (auth: {user.auth_provider})")
    else:
        print("get_current_user returning None")

    return user

@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_google_callback')
    print("Generate Redirect URI for Google: ", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/login/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request, response: Response, db: Session = Depends(get_db)):
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
    user = db.query(models.User).filter(models.User.google_id == google_id).first()

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
            db.commit()
            db.refresh(user)

    else:
        # --- Case 2: No User Found by Google ID - Check for email conflict and Create New ---
        print(f"No user found for Google ID {google_id}. Checking email {email} and creating new user.")
        # Check if another user already exists with this email (conflict)
        existing_email_user = db.query(models.User).filter(models.User.email == email).first()
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
        db.commit()
        db.refresh(user)
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
async def logout(request: Request, response: Response):
    request.session.pop('user_id', None) # Pop user_id from session
    # Also clear the guest cookie on explicit logout
    response.delete_cookie(GUEST_USER_ID_COOKIE)
    print('successfully logged out user')
    # RedirectResponse needs to be returned, not just called
    redirect_resp = RedirectResponse(url=settings.frontend_base_url)
    # Need to set the cookie deletion on the actual response being returned
    redirect_resp.delete_cookie(GUEST_USER_ID_COOKIE)
    return redirect_resp

# --- Keep Endpoint to Create Guest User ---
# Even if not used during login, it's needed for the initial guest creation flow
class GuestUserResponse(BaseModel):
    guest_user_id: uuid.UUID

@router.post("/users/guest", response_model=GuestUserResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_user(response: Response, db: Session = Depends(get_db)):
    guest_user = models.User(auth_provider=None) # Create user with no auth provider
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    print(f"Created guest user: {guest_user.id}")

    # Set the guest user ID in an HttpOnly cookie
    response.set_cookie(
        key=GUEST_USER_ID_COOKIE,
        value=str(guest_user.id),
        httponly=True,
        samesite="lax",
        # secure=True, # Uncomment for production HTTPS
        max_age=60*60*24*365 # Example: 1 year expiry
    )
    return GuestUserResponse(guest_user_id=guest_user.id)