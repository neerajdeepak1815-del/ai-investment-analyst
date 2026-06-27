import logging
import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


def _is_railway_url(url: str) -> bool:
    u = (url or "").lower()
    return "railway" in u or "rlwy.net" in u


_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    if "sslmode=" not in settings.database_url:
        # Railway public proxy requires SSL; private network prefers SSL too.
        _connect_args["sslmode"] = "require" if _is_railway_url(settings.database_url) else "prefer"

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_db_initialized = False
_db_init_error: Optional[str] = None


def db_is_ready() -> bool:
    return _db_initialized


def db_init_error() -> Optional[str]:
    return _db_init_error


def init_db() -> bool:
    """Create tables if needed. Returns True on success; does not crash the process."""
    global _db_initialized, _db_init_error
    if _db_initialized:
        return True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
        _db_initialized = True
        _db_init_error = None
        logger.info("Database connected and tables ready.")
        return True
    except Exception as exc:
        _db_init_error = str(exc)
        logger.error(
            "Database startup failed: %s. "
            "Railway: (1) Postgres + web service SAME region "
            "(2) DATABASE_URL=${{Postgres.DATABASE_URL}} on web service "
            "(3) if cross-region, set DATABASE_PUBLIC_URL=${{Postgres.DATABASE_PUBLIC_URL}}",
            exc,
        )
        return False


def get_db():
    if not _db_initialized:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "error": _db_init_error or "Database not connected",
                "fix": (
                    "Railway: Postgres + web service in SAME region; "
                    "DATABASE_URL=${{Postgres.DATABASE_URL}}; "
                    "see /health/diagnostics"
                ),
            },
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
