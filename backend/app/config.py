from typing import Any

import os

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_cloud_host() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER"))


def _normalize_database_url(url: str) -> str:
    """Railway/Heroku often provide postgres:// — SQLAlchemy needs postgresql+psycopg2://."""
    u = (url or "").strip()
    if u.startswith("postgres://"):
        return "postgresql+psycopg2://" + u[len("postgres://") :]
    if u.startswith("postgresql://") and not u.startswith("postgresql+"):
        return "postgresql+psycopg2://" + u[len("postgresql://") :]
    return u


def _resolve_database_url_from_env() -> str:
    """Pick Railway Postgres URL: private first, public when cross-region."""
    private = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    if not private and public:
        return _normalize_database_url(public)
    if private and "railway.internal" in private and public:
        # Cross-region: private hostname is unreachable from another region.
        return _normalize_database_url(public)
    if private:
        return _normalize_database_url(private)
    return ""


class Settings(BaseSettings):
    app_name: str = "AI Investment Analyst"
    app_env: str = "dev"
    database_url: str = "sqlite:///./investment_analyst.db"
    recommendation_threshold: float = 75.0
    recommendation_hysteresis_buffer: float = 4.0
    recommendation_hysteresis_minutes: int = 1440
    auto_refresh_enabled: bool = True
    auto_refresh_interval_minutes: int = 15
    # Leaderboard: penalize final_score when headline news_risk is above neutral (see news_risk.py).
    news_ranking_weight: float = 5.0
    news_risk_neutral: float = 32.0
    risk_block_min_confidence: str = "medium"
    alert_webhook_url: str = ""
    # Set AUTH_ENABLED=true (env) to require login again.
    auth_enabled: bool = False
    auth_username: str = "admin"
    auth_password: str = "GoatAnalyst99"
    auth_session_cookie: str = "aiia_session"
    # Optional: reliable quotes on cloud hosts (Yahoo often blocks datacenters).
    # Use QUOTE_API_FINNHUB or IIA_FINNHUB_TOKEN on Railway if a broken "Finnhub" build secret blocks deploy.
    finnhub_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "FINNHUB_API_KEY",
            "QUOTE_API_FINNHUB",
            "IIA_FINNHUB_TOKEN",
            "finnhub_api_key",
            "FinnhubApiKey",
        ),
    )
    # Optional fallback: https://www.alphavantage.co/support/#api-key
    alphavantage_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ALPHAVANTAGE_API_KEY", "alphavantage_api_key", "ALPHA_VANTAGE_API_KEY"),
    )
    # Optional: https://twelvedata.com/ (800 calls/day free)
    twelve_data_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("TWELVE_DATA_API_KEY", "twelve_data_api_key", "TWELVEDATA_API_KEY"),
    )
    # Optional: domain-filtered headlines on GET /recommendations/{ticker} (investor_news). Falls back to Google News RSS.
    newsapi_key: str = Field(
        default="",
        validation_alias=AliasChoices("NEWSAPI_KEY", "newsapi_key", "NEWS_API_KEY"),
    )
    # Trusted-outlet substring filter for investor news (and legacy critical-event helpers in code).
    critical_news_strict_outlets: bool = Field(
        default=True,
        validation_alias=AliasChoices("CRITICAL_NEWS_STRICT_OUTLETS", "critical_news_strict_outlets"),
    )
    critical_news_allowlist: str = Field(
        default=(
            "reuters,bloomberg,wall street journal,wsj,financial times,ft.com,"
            "associated press,ap news,cnbc,bbc,the economist,new york times,nytimes,"
            "washington post,barron,barrons,nikkei,dow jones,marketwatch,fortune,"
            "investopedia,japan times,japantimes"
        ),
        validation_alias=AliasChoices("CRITICAL_NEWS_ALLOWLIST", "critical_news_allowlist"),
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> Any:
        env_url = _resolve_database_url_from_env()
        raw = v
        if isinstance(raw, str) and raw.strip():
            raw = raw.strip()
        elif env_url:
            raw = env_url
        else:
            raw = ""

        if not raw:
            if _is_cloud_host():
                raise ValueError(
                    "DATABASE_URL is not set. On Railway: add PostgreSQL (same region as web service), "
                    "then Variables → DATABASE_URL=${{Postgres.DATABASE_URL}}. "
                    "If regions differ, also add DATABASE_PUBLIC_URL=${{Postgres.DATABASE_PUBLIC_URL}}."
                )
            return "sqlite:///./investment_analyst.db"
        return _normalize_database_url(str(raw))

    @model_validator(mode="after")
    def require_postgres_on_cloud(self) -> "Settings":
        if _is_cloud_host() and self.database_url.startswith("sqlite"):
            raise ValueError(
                "DATABASE_URL must use PostgreSQL on Railway/Render (SQLite is local-dev only). "
                "Add PostgreSQL to the project and reference it: DATABASE_URL=${{Postgres.DATABASE_URL}}"
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
