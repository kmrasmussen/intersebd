from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str

    # Add fields for the environment variables causing the error
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    # Also add the session key we configured earlier
    session_secret_key: str
    frontend_base_url: str
    openrouter_provisioning_api_key: str
    openrouter_provisioning_api_base_url: str
    openrouter_provisioning_api_guest_limit: int

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Tell pydantic to ignore other env vars not defined here

settings = Settings()