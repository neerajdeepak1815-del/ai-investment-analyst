"""Shared Yahoo Finance data helpers for Market Opportunities (free endpoints only)."""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

YAHOO_QUOTE_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def yahoo_symbol(ticker: str) -> str:
    t = (ticker or "").upper().strip()
    if t == "BRK-B":
        return "BRK-B"
    return t.replace(".", "-")


def _browser_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _raw_num(obj: Any) -> Optional[float]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        if "raw" in obj and obj["raw"] is not None:
            try:
                v = float(obj["raw"])
                return None if math.isnan(v) else v
            except (TypeError, ValueError):
                pass
        if "fmt" in obj:
            try:
                return float(str(obj["fmt"]).replace(",", "").replace("%", ""))
            except (TypeError, ValueError):
                return None
    try:
        v = float(obj)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _parse_yahoo_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(val, dict) and val.get("raw") is not None:
        return _parse_yahoo_dt(val["raw"])
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_quote_summary(ticker: str) -> Optional[dict[str, Any]]:
    """Yahoo quoteSummary — calendar, earnings history, estimates, price."""
    sym = yahoo_symbol(ticker)
    try:
        r = requests.get(
            YAHOO_QUOTE_SUMMARY.format(symbol=sym),
            params={
                "modules": "calendarEvents,earningsHistory,earningsTrend,financialData,price,summaryProfile",
            },
            headers=_browser_headers(),
            timeout=12,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        payload = r.json()
        result = (payload.get("quoteSummary") or {}).get("result") or []
        if not result:
            return None
        return result[0]
    except Exception as exc:
        logger.debug("quoteSummary %s: %s", sym, exc)
        return None


def fetch_chart_closes(symbol: str, days: int = 400) -> Optional[list[float]]:
    """Adjusted close series via Yahoo chart API (works when yfinance is flaky)."""
    sym = yahoo_symbol(symbol) if symbol != "^VIX" else "^VIX"
    try:
        r = requests.get(
            YAHOO_CHART.format(symbol=requests.utils.quote(sym, safe="")),
            params={
                "interval": "1d",
                "range": "2y" if days >= 300 else "1y",
            },
            headers=_browser_headers(),
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return None
        quotes = (result[0].get("indicators") or {}).get("quote") or []
        if not quotes:
            return None
        closes = quotes[0].get("close") or []
        out = [float(c) for c in closes if c is not None and not (isinstance(c, float) and math.isnan(c))]
        return out if len(out) >= 20 else None
    except Exception as exc:
        logger.debug("chart %s: %s", sym, exc)
        return None


def fetch_history_closes(symbol: str, days: int = 400) -> Optional[list[float]]:
    """Price history: yfinance first, Yahoo chart fallback."""
    sym = yahoo_symbol(symbol) if not symbol.startswith("^") else symbol
    try:
        import yfinance as yf

        end = datetime.now()
        start = end - timedelta(days=days)
        hist = yf.Ticker(sym).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
        )
        if hist is not None and len(hist) >= 20:
            closes = [float(x) for x in hist["Close"].tolist() if x == x]
            if len(closes) >= 20:
                return closes
    except Exception as exc:
        logger.debug("yfinance history %s: %s", sym, exc)
    return fetch_chart_closes(sym, days=days)


def trading_day_return(closes: list[float], trading_days: int) -> Optional[float]:
    """Total return over N trading sessions (not calendar days)."""
    if len(closes) < trading_days + 1:
        return None
    base = closes[-(trading_days + 1)]
    if base <= 0:
        return None
    return (closes[-1] / base - 1.0) * 100.0


def percentile_rank_score(values: list[float], idx: int, max_pts: float) -> float:
    """Average-rank percentile (handles ties correctly)."""
    n = len(values)
    if n <= 1:
        return max_pts / 2.0
    v = values[idx]
    less = sum(1 for x in values if x < v)
    equal = sum(1 for x in values if x == v)
    avg_rank = less + (equal - 1) / 2.0
    return (avg_rank / (n - 1)) * max_pts


def compute_rsi_wilder(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def parse_earnings_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract upcoming earnings + last 4 quarters surprise history from quoteSummary."""
    out: dict[str, Any] = {
        "upcoming_date": None,
        "upcoming_dates": [],
        "eps_estimate": None,
        "earnings_high": None,
        "earnings_low": None,
        "current_price": None,
        "target_price": None,
        "sector": None,
        "name": None,
        "surprise_history": [],
        "beats": 0,
        "misses": 0,
    }

    profile = summary.get("summaryProfile") or {}
    out["sector"] = profile.get("sector") or profile.get("industry")
    out["name"] = profile.get("longName") or profile.get("shortName")

    fin = summary.get("financialData") or {}
    price_mod = summary.get("price") or {}
    out["current_price"] = _raw_num(fin.get("currentPrice")) or _raw_num(price_mod.get("regularMarketPrice"))
    out["target_price"] = _raw_num(fin.get("targetMeanPrice"))

    cal = (summary.get("calendarEvents") or {}).get("earnings") or {}
    out["eps_estimate"] = _raw_num(cal.get("earningsAverage"))
    out["earnings_high"] = _raw_num(cal.get("earningsHigh"))
    out["earnings_low"] = _raw_num(cal.get("earningsLow"))

    upcoming: list[datetime] = []
    for key in ("earningsDate", "earningsDates"):
        raw = cal.get(key)
        if raw is None:
            continue
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            dt = _parse_yahoo_dt(item)
            if dt:
                upcoming.append(dt)
    upcoming = sorted(set(upcoming))
    out["upcoming_dates"] = [d.date().isoformat() for d in upcoming]
    if upcoming:
        out["upcoming_date"] = upcoming[0].date().isoformat()

    hist_rows = (summary.get("earningsHistory") or {}).get("history") or []
    surprise_history: list[dict[str, Any]] = []
    beats = misses = 0
    for row in hist_rows[-4:]:
        actual = _raw_num(row.get("epsActual"))
        est = _raw_num(row.get("epsEstimate"))
        surprise_pct = _raw_num(row.get("surprisePercent"))
        quarter = (row.get("quarter") or {}).get("fmt") if isinstance(row.get("quarter"), dict) else row.get("quarter")
        if actual is None or est is None:
            continue
        beat = actual >= est
        if beat:
            beats += 1
        else:
            misses += 1
        if surprise_pct is None and est != 0:
            surprise_pct = (actual - est) / abs(est) * 100.0
        surprise_history.append(
            {
                "quarter": str(quarter) if quarter else None,
                "actual": round(actual, 4),
                "estimate": round(est, 4),
                "surprise_pct": round(surprise_pct, 2) if surprise_pct is not None else None,
                "beat": beat,
            }
        )
    out["surprise_history"] = surprise_history
    out["beats"] = beats
    out["misses"] = misses
    return out


def parse_earnings_from_yfinance_df(ticker: str) -> Optional[dict[str, Any]]:
    """Fallback: yfinance earnings_dates DataFrame."""
    try:
        import yfinance as yf

        t = yf.Ticker(yahoo_symbol(ticker))
        df = None
        try:
            df = t.get_earnings_dates(limit=12)
        except Exception:
            df = getattr(t, "earnings_dates", None)

        if df is None or getattr(df, "empty", True):
            return None

        upcoming_date = None
        surprise_history: list[dict[str, Any]] = []
        beats = misses = 0
        now = datetime.now(timezone.utc)

        for idx, row in df.iterrows():
            dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else _parse_yahoo_dt(str(idx))
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            reported = row.get("Reported EPS")
            estimate = row.get("EPS Estimate")
            surprise = row.get("Surprise(%)")
            event_type = str(row.get("Event Type", "")).lower()

            if "meeting" in event_type:
                continue

            has_reported = reported is not None and reported == reported  # not NaN
            has_estimate = estimate is not None and estimate == estimate

            if not has_reported and dt.date() >= now.date() and upcoming_date is None:
                upcoming_date = dt.date().isoformat()

            if has_reported and has_estimate:
                actual = float(reported)
                est = float(estimate)
                beat = actual >= est
                if beat:
                    beats += 1
                else:
                    misses += 1
                sp = float(surprise) if surprise is not None and surprise == surprise else None
                surprise_history.append(
                    {
                        "quarter": dt.date().isoformat(),
                        "actual": round(actual, 4),
                        "estimate": round(est, 4),
                        "surprise_pct": round(sp, 2) if sp is not None else None,
                        "beat": beat,
                    }
                )

        if not upcoming_date and not surprise_history:
            return None

        return {
            "upcoming_date": upcoming_date,
            "upcoming_dates": [upcoming_date] if upcoming_date else [],
            "surprise_history": surprise_history[-4:],
            "beats": sum(1 for x in surprise_history[-4:] if x["beat"]),
            "misses": sum(1 for x in surprise_history[-4:] if not x["beat"]),
        }
    except Exception as exc:
        logger.debug("yfinance earnings_dates %s: %s", ticker, exc)
        return None
