from src.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_IqsFnZ0e5uMX@ep-wandering-heart-a44wquzu-pooler.us-east-1.aws.neon.tech/neondb"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session factory
async_session_maker = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Create tables asynchronously
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Async generator for dependency injection
async def get_session():
    async with async_session_maker() as session:
        yield session
