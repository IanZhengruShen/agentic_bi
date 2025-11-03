"""
Database session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
import os

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:devpassword123@postgres:5432/agentic_bi"
)

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True if os.getenv("ENV") == "development" else False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session maker
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database sessions.

    Usage in FastAPI:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
