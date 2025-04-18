import logging # Make sure logging is imported
from starlette.middleware.base import BaseHTTPMiddleware # Keep this
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send # Import common types
from typing import List, Set, Callable, Awaitable # Import Callable, Awaitable for type hint

# Define the type hint alias if needed, matching older Starlette versions
RequestResponseCall = Callable[[Request], Awaitable[Response]]


class EnforceStrictCORSPostMiddleware(BaseHTTPMiddleware):
    """
    This middleware runs AFTER the main CORSMiddleware and routing.
    It enforces strict origin checks for non-public paths by removing
    CORS headers if the origin doesn't match the strict list.
    """
    def __init__(self, app: ASGIApp, strict_origins: List[str], public_path_prefix: str = "/public-api"):
        super().__init__(app)
        self.strict_origins: Set[str] = set(strict_origins) # Use a set for faster lookups
        self.public_path_prefix: str = public_path_prefix
        self.logger = logging.getLogger(__name__ + ".EnforceStrictCORSPostMiddleware") # Logger specific to this middleware


    async def dispatch(self, request: Request, call_next: RequestResponseCall) -> Response: # Use the defined type hint
        response = await call_next(request)
        is_public_path = request.url.path.startswith(self.public_path_prefix)
        origin = request.headers.get("origin")

        if not is_public_path and origin:
            is_strictly_allowed = origin in self.strict_origins
            if not is_strictly_allowed:
                if 'access-control-allow-origin' in response.headers:
                    self.logger.debug(f"Removing ACAO header for non-public path '{request.url.path}' from origin '{origin}'")
                    del response.headers['access-control-allow-origin']
                if 'access-control-allow-credentials' in response.headers:
                     self.logger.debug(f"Removing ACAC header for non-public path '{request.url.path}' from origin '{origin}'")
                     del response.headers['access-control-allow-credentials']
        return response