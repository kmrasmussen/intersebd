import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# --- Security Scheme ---
bearer_scheme = HTTPBearer(
    description="Enter your Intercept Key prefixed with 'Bearer ' (e.g., 'Bearer sk-...')"
)

# --- Reusable Dependency for Authorization Header ---
async def get_intercept_key_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> str:
    """
    Dependency function to extract the intercept key from the
    Authorization: Bearer header credentials provided by HTTPBearer.
    """
    # CORRECTED: Return only the credentials part
    intercept_key = credentials.credentials

    # Optional validation can remain here
    # if not intercept_key.startswith("sk-"): ...

    logger.debug(f"Extracted intercept key (last 4 chars): ...{intercept_key[-4:]}")
    return intercept_key # Return just the key