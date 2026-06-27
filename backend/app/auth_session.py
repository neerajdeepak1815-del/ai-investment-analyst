"""Stateless signed session cookies — survives Railway restarts and multiple replicas."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

from app.config import settings


def _signing_key() -> bytes:
    secret = (os.getenv("AUTH_SESSION_SECRET") or settings.auth_password or "dev-insecure").encode()
    return secret


def cookie_secure() -> bool:
    raw = (os.getenv("AUTH_COOKIE_SECURE") or "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or settings.app_env == "production")


def create_session_token(username: str, max_age_seconds: int = 86400) -> str:
    exp = int(time.time()) + max_age_seconds
    payload = f"{username}|{exp}"
    sig = hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_session_token(token: str) -> bool:
    if not token:
        return False
    try:
        payload, sig = token.rsplit("|", 1)
        expected = hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        username, exp_str = payload.split("|", 1)
        if username != settings.auth_username:
            return False
        return int(exp_str) >= int(time.time())
    except (ValueError, TypeError):
        return False
