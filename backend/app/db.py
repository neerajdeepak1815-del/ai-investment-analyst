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
_db_urls_tried: list[str] = []
_db_last_host: str = ""


def _host_hint(url: str) -> str:
    try:
        from urllib.parse import urlparse

        p = urlparse(url.replace("+psycopg2", ""))
        return p.hostname or "unknown"
    except Exception:
        return "unknown"


def _mask_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        p = urlparse(url.replace("+psycopg2", ""))
        host = p.hostname or "unknown"
        return f"{p.scheme}://***@{host}:{p.port or 5432}{p.path or ''}"
    except Exception:
        return "unparseable"


def db_urls_tried() -> list[str]:
    return list(_db_urls_tried)


def db_last_host() -> str:
    return _db_last_host


def db_env_summary() -> dict:
    """Masked env hints for /setup — no credentials."""
    raw_url = os.getenv("DATABASE_URL", "").strip()
    raw_private = os.getenv("DATABASE_PRIVATE_URL", "").strip()
    raw_public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    return {
        "database_url_env_set": bool(raw_url),
        "database_url_env_host": _mask_url(_normalize_database_url(raw_url)) if raw_url else None,
        "database_url_uses_public_proxy": "rlwy.net" in raw_url.lower(),
        "database_private_url_env_set": bool(raw_private),
        "database_public_url_env_set": bool(raw_public),
        "resolved_settings_host": _mask_url(settings.database_url),
        "uses_railway_internal": "railway.internal" in settings.database_url.lower(),
    }


def db_is_ready() -> bool:
    return _db_initialized


def db_init_error() -> Optional[str]:
    return _db_init_error


def _dns_unreachable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "could not translate host",
            "name or service not known",
            "temporary failure in name resolution",
            "nodename nor servname provided",
        )
    )


def init_db() -> bool:
    """Create tables if needed. Retries transient Railway proxy errors."""
    import time

    global engine, SessionLocal, _db_initialized, _db_init_error, _db_urls_tried, _db_last_host
    if _db_initialized:
        return True

    last_exc: Optional[Exception] = None
    urls = _candidate_database_urls()
    _db_urls_tried = [_mask_url(u) for u in urls]
    private_dns_failed = False

    for attempt in range(3):
        for url in urls:
            host = _host_hint(url)
            _db_last_host = host
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
                logger.info("Database connected (%s, %s) and tables ready.", host_hint, host)
                return True
            except Exception as exc:
                last_exc = exc
                if _is_railway_private_url(url) and _dns_unreachable(exc):
                    private_dns_failed = True
                    logger.warning(
                        "Private Postgres host unreachable (%s) — web service is likely in a different region than Postgres.",
                        host,
                    )
                    continue
                if _transient_db_error(exc):
                    logger.warning(
                        "Database connect attempt %s failed (%s): %s",
                        attempt + 1,
                        host,
                        exc,
                    )
                    continue
                break
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))

    if private_dns_failed and last_exc and "rlwy.net" in str(last_exc).lower():
        _db_init_error = (
            "Private Postgres (railway.internal) is unreachable from this region, and the public proxy "
            f"({ _db_last_host }) also failed. Fix: move the Meridian web service to the SAME region as "
            "Postgres (Railway → web service → Settings → Region), set "
            "DATABASE_URL=${{Postgres.DATABASE_URL}}, remove DATABASE_PUBLIC_URL, then redeploy both services."
        )
    elif private_dns_failed:
        _db_init_error = (
            "Private Postgres (railway.internal) is unreachable — your web service and Postgres are in "
            "different Railway regions. Move Meridian to the same region as Postgres, use "
            "DATABASE_URL=${{Postgres.DATABASE_URL}}, remove DATABASE_PUBLIC_URL, and redeploy."
        )
    elif "rlwy.net" in (_db_last_host or ""):
        raw_url = os.getenv("DATABASE_URL", "")
        if "rlwy.net" in raw_url.lower():
            _db_init_error = (
                f"DATABASE_URL points at the public proxy ({_db_last_host}), which is failing. "
                "Change it to DATABASE_URL=${{Postgres.DATABASE_URL}} (private), put web + Postgres in "
                "the same region, remove DATABASE_PUBLIC_URL, redeploy Postgres, then redeploy Meridian."
            )
        else:
            _db_init_error = (
                f"Public Postgres proxy ({_db_last_host}) failed after private URL attempts. "
                "Move Meridian to the same region as Postgres and use the private DATABASE_URL. "
                f"Last error: {last_exc}"
            )
    else:
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
