import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/agrops",
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Motor async (API). pool_pre_ping + recycle evitan conexiones huérfanas tras
# reinicios de Postgres / Docker Desktop en Windows.
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=30,
    connect_args={
        "timeout": 10,
        "command_timeout": 60,
        "server_settings": {"application_name": "agrops-api"},
    },
)

# Motor sync solo si hace falta (p. ej. scripts). asyncpg no sirve aquí.
_SYNC_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
sync_engine = create_engine(
    _SYNC_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=2,
    max_overflow=5,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    """Cede una AsyncSession por petición y la cierra al terminar."""
    async with AsyncSessionLocal() as db:
        yield db
