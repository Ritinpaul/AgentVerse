import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentos.db")
APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "local"))

if APP_ENV.lower() == "production" and "sqlite" in DATABASE_URL.lower():
    raise RuntimeError(
        f"APP_ENV=production but DATABASE_URL points to SQLite ({DATABASE_URL}). "
        "Refusing to start. Set DATABASE_URL to a PostgreSQL connection string."
    )

# Determine engine type (sync or async) based on database driver
is_async = "asyncpg" in DATABASE_URL or "aiosqlite" in DATABASE_URL

if is_async:
    connect_args = {"statement_cache_size": 0, "prepared_statement_cache_size": 0} if "asyncpg" in DATABASE_URL else {}
    async_engine = create_async_engine(DATABASE_URL, echo=(APP_ENV == "local"), connect_args=connect_args)
    sync_url = DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url, echo=(APP_ENV == "local"))
else:
    sync_engine = create_engine(DATABASE_URL, echo=(APP_ENV == "local"))

engine = sync_engine

def create_db_and_tables():
    SQLModel.metadata.create_all(sync_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_db_and_tables()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").warning(f"Database init warning: {e}")
    yield
    pass

app = FastAPI(
    title="AgentOS Control Plane",
    description="Manages agent lifecycles and fleet operations.",
    lifespan=lifespan
)

# CORS configuration: avoid wildcard * when allow_credentials=True
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://app.nuuvixx.com",
        "https://store.nuuvixx.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import lifecycle, registry, swarms

app.include_router(lifecycle.router)
app.include_router(registry.router)
app.include_router(swarms.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "control-plane"}
