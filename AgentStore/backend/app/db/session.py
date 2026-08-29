from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
if "?" in db_url and "sqlite" not in db_url:
    db_url = db_url.split("?")[0]
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if not db_url.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    db_url,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
