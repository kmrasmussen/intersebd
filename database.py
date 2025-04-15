# filepath: /home/kasper/randomrepos/intercept_calls/database.py
import psycopg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import os
import logging
from config import settings

logger = logging.getLogger(__name__)


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