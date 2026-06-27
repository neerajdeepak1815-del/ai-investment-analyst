import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True}

if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    if "sslmode=" not in settings.database_url:
        _connect_args["sslmode"] = "prefer"

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_db_initialized = False


def init_db() -> None:
    """Create tables if needed. Called once at app startup."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
        _db_initialized = True
        logger.info("Database connected and tables ready.")
    except Exception as exc:
        logger.error(
            "Database startup failed (%s). Check DATABASE_URL on Railway: "
            "add PostgreSQL and set DATABASE_URL=${{Postgres.DATABASE_URL}} on the web service.",
            exc,
        )
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
