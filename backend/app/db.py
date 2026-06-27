import logging
import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import _normalize_database_url, settings

logger = logging.getLogger(__name__)


def _is_railway_url(url: str) -> bool:
    u = (url or "").lower()
    return "railway" in u or "rlwy.net" in u


def _connect_args_for(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("postgresql") and "sslmode=" not in url:
        return {"sslmode": "require" if _is_railway_url(url) else "prefer"}
    return {}


def _candidate_database_urls() -> list[str]:
    """URLs to try in order (public first when private host is railway.internal)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        if not raw:
            return
        u = _normalize_database_url(raw.strip())
        if u not in seen:
            seen.add(u)
            out.append(u)

    private = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()

    # Cross-region: public URL must be tried first (private .internal won't resolve).
    if private and "railway.internal" in private and public:
        add(public)
        add(private)
    else:
        add(settings.database_url)
        if public:
            add(public)
        if private:
            add(private)

    return out


def _make_engine(url: str):
    return create_engine(
        url,
        connect_args=_connect_args_for(url),
        pool_pre_ping=True,
    )


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_db_initialized = False
_db_init_error: Optional[str] = None


def db_is_ready() -> bool:
    return _db_initialized


def db_init_error() -> Optional[str]:
    return _db_init_error


def init_db() -> bool:
    """Create tables if needed. Tries public URL when railway.internal is unreachable."""
    global engine, SessionLocal, _db_initialized, _db_init_error
    if _db_initialized:
        return True

    last_exc: Optional[Exception] = None
    for url in _candidate_database_urls():
        try:
            eng = _make_engine(url)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=eng)
            engine = eng
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            _db_initialized = True
            _db_init_error = None
            host_hint = "public" if "rlwy.net" in url or "proxy.rlwy.net" in url else "private"
            logger.info("Database connected (%s host) and tables ready.", host_hint)
            return True
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "railway.internal" in url or "could not translate host" in msg or "name or service not known" in msg:
                logger.warning("Database URL unreachable (%s), trying next candidate.", url.split("@")[-1][:40])
                continue
            break

    _db_init_error = str(last_exc) if last_exc else "Unknown database error"
    logger.error(
        "Database startup failed: %s. "
        "Railway fix: add DATABASE_PUBLIC_URL=${{Postgres.DATABASE_PUBLIC_URL}} on the web service, "
        "OR move web service to the same region as Postgres.",
        _db_init_error,
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
                    "Add DATABASE_PUBLIC_URL=${{Postgres.DATABASE_PUBLIC_URL}} on the web service, "
                    "or move Meridian to the same region as Postgres."
                ),
            },
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
