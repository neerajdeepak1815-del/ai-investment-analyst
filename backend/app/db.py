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


def _is_railway_private_url(url: str) -> bool:
    return "railway.internal" in (url or "").lower()


def _connect_args_for(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if not url.startswith("postgresql"):
        return {}

    args: dict = {"connect_timeout": 30}
    u = url.lower()

    if _is_railway_private_url(url):
        # Railway private network — SSL not required (and can cause handshake drops).
        if "sslmode=" not in url:
            args["sslmode"] = "disable"
    elif "rlwy.net" in u or "proxy.rlwy.net" in u:
        # Public TCP proxy — require SSL + keepalives to reduce dropped connections.
        if "sslmode=" not in url:
            args["sslmode"] = "require"
        args.update(
            {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
        )
    elif _is_railway_url(url) and "sslmode=" not in url:
        args["sslmode"] = "require"
    elif "sslmode=" not in url:
        args["sslmode"] = "prefer"
    return args


def _candidate_database_urls() -> list[str]:
    """URLs to try in order — private first (stable), public last (cross-region fallback)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        if not raw:
            return
        u = _normalize_database_url(raw.strip())
        if u not in seen:
            seen.add(u)
            out.append(u)

    private_ref = os.getenv("DATABASE_PRIVATE_URL", "").strip()
    private = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()

    # Same-region Railway: private URL is reliable (no public proxy).
    if private_ref:
        add(private_ref)
    if private and "railway.internal" in private:
        add(private)
    add(settings.database_url)
    if private and "railway.internal" not in private:
        add(private)
    if public:
        add(public)

    return out


def _make_engine(url: str):
    return create_engine(
        url,
        connect_args=_connect_args_for(url),
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
    )


def _transient_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "server closed the connection",
            "connection reset",
            "ssl connection",
            "connection timed out",
            "could not translate host",
            "name or service not known",
        )
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
    """Create tables if needed. Retries transient Railway proxy errors."""
    import time

    global engine, SessionLocal, _db_initialized, _db_init_error
    if _db_initialized:
        return True

    last_exc: Optional[Exception] = None
    urls = _candidate_database_urls()

    for attempt in range(3):
        for url in urls:
            try:
                eng = _make_engine(url)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                Base.metadata.create_all(bind=eng)
                engine = eng
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                _db_initialized = True
                _db_init_error = None
                if _is_railway_private_url(url):
                    host_hint = "private"
                elif "rlwy.net" in url:
                    host_hint = "public-proxy"
                else:
                    host_hint = "direct"
                logger.info("Database connected (%s) and tables ready.", host_hint)
                return True
            except Exception as exc:
                last_exc = exc
                if _transient_db_error(exc):
                    logger.warning(
                        "Database connect attempt %s failed (%s): %s",
                        attempt + 1,
                        url.split("@")[-1][:48],
                        exc,
                    )
                    continue
                break
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))

    _db_init_error = str(last_exc) if last_exc else "Unknown database error"
    logger.error("Database startup failed: %s", _db_init_error)
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
