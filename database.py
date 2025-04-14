# filepath: /home/kasper/randomrepos/intercept_calls/database.py
import psycopg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import os
import logging

logger = logging.getLogger("yoness")

class Settings(BaseSettings):
    # Default to the value in docker-compose if DATABASE_URL env var is not set
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres/intercept")

    class Config:
        env_file = '.env' # Optional: Load from .env file if needed

settings = Settings()

# Use asyncpg for the database connection
engine = create_async_engine(settings.database_url, echo=True) # echo=True for debugging SQL

# Async session maker
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit() # Commit changes made within the session block