"""
Earnings radar — Post-Earnings Announcement Drift (Bernard & Thomas, 1989).

Uses Yahoo quoteSummary (primary) + yfinance earnings_dates (fallback).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from app.opportunities.universe import ticker_meta
from app.opportunities.yahoo_data import (
    fetch_quote_summary,
    parse_earnings_from_summary,
    parse_earnings_from_yfinance_df,
)

logger = logging.getLogger(__name__)

EARNINGS_WINDOW_DAYS = 14


def _pick_upcoming_date(dates: list[str], window_days: int = EARNINGS_WINDOW_DAYS) -> Optional[str]:
    today = date.today()
    end = today + timedelta(days=window_days)
    valid: list[date] = []
    for ds in dates:
        try:
            d = date.fromisoformat(str(ds)[:10])
        except ValueError:
            continue
        if today - timedelta(days=1) <= d <= end:
            valid.append(d)
    if not valid:
        return None
    return min(valid).isoformat()


def _fetch_earnings(ticker: str) -> Optional[dict[str, Any]]:
    meta = ticker_meta(ticker)
    bundle: dict[str, Any] = {}

    summary = fetch_quote_summary(ticker)
    if summary:
        bundle = parse_earnings_from_summary(summary)

    if not bundle.get("upcoming_date") and not bundle.get("surprise_history"):
        yf_bundle = parse_earnings_from_yfinance_df(ticker)
        if yf_bundle:
            for k, v in yf_bundle.items():
                if bundle.get(k) in (None, [], 0) and v not in (None, [], 0):
                    bundle[k] = v

    upcoming_candidates: list[str] = []
    if bundle.get("upcoming_date"):
        upcoming_candidates.append(bundle["upcoming_date"])
    upcoming_candidates.extend(bundle.get("upcoming_dates") or [])

    earnings_date = _pick_upcoming_date(upcoming_candidates)
    if earnings_date is None:
        return None

    try:
        ed = date.fromisoformat(earnings_date)
    except ValueError:
        return None

    today = date.today()
    days_until = (ed - today).days

    name = bundle.get("name") or meta["name"]
    sector = bundle.get("sector") or meta["sector"]
    current_price = bundle.get("current_price")
    target_price = bundle.get("target_price")
    eps_estimate = bundle.get("eps_estimate")

    upside_pct = None
    if target_price and current_price and current_price > 0:
        upside_pct = round((target_price - current_price) / current_price * 100, 2)

    surprise_history = bundle.get("surprise_history") or []
    beats = int(bundle.get("beats") or 0)
    misses = int(bundle.get("misses") or 0)

    earnings_time = None

    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "earnings_date": earnings_date,
        "earnings_time": earnings_time,
        "current_price": round(float(current_price), 2) if current_price else None,
        "eps_estimate": round(float(eps_estimate), 2) if eps_estimate is not None else None,
        "eps_estimate_low": round(float(bundle["earnings_low"]), 2) if bundle.get("earnings_low") is not None else None,
        "eps_estimate_high": round(float(bundle["earnings_high"]), 2) if bundle.get("earnings_high") is not None else None,
        "target_price": round(float(target_price), 2) if target_price else None,
        "upside_pct": upside_pct,
        "surprise_history": surprise_history,
        "beats": beats,
        "misses": misses,
        "total_quarters": beats + misses,
        "days_until": days_until,
        "data_source": "yahoo_quote_summary" if summary else "yfinance_fallback",
    }


def _assign_flag(item: dict[str, Any], meridian_scores: dict[str, float]) -> dict[str, Any]:
    beats = item.get("beats", 0)
    misses = item.get("misses", 0)
    total = item.get("total_quarters", 0)
    ticker = item["ticker"]
    meridian = meridian_scores.get(ticker)

    item["meridian_score"] = round(meridian, 1) if meridian is not None else None

    if beats >= 3 and total >= 3 and (meridian is None or meridian >= 65):
        item["flag"] = "green"
        item["flag_label"] = "Consistent Beater — Watch for Continuation"
    elif misses >= 2:
        item["flag"] = "red"
        item["flag_label"] = "Caution — Miss Risk"
    else:
        item["flag"] = "amber"
        item["flag_label"] = "Monitor"

    if item["flag"] == "green":
        days = item.get("days_until", 0)
        item["setup"] = {
            "entry_window": (
                f"{max(1, days - 7)} to {max(1, days - 2)} days before earnings"
                if days > 2
                else "Earnings imminent — elevated risk"
            ),
            "risk_note": "Earnings are binary events — position size accordingly (1–3% of portfolio max).",
            "drift_note": "PEAD research: consistent beaters often drift upward 4–8 weeks post-report when surprise is modest.",
        }

    return item


def scan_earnings(
    universe: list[str],
    meridian_scores: dict[str, float] | None = None,
    window_days: int = EARNINGS_WINDOW_DAYS,
) -> dict[str, Any]:
    if meridian_scores is None:
        meridian_scores = {}

    results: list[dict[str, Any]] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_earnings, t): t for t in universe}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r is not None:
                    results.append(_assign_flag(r, meridian_scores))
            except Exception as exc:
                errors += 1
                logger.debug("earnings scan %s: %s", futures[fut], exc)

    flag_order = {"green": 0, "amber": 1, "red": 2}
    results.sort(key=lambda r: (flag_order.get(r.get("flag", "amber"), 1), r.get("days_until", 99)))

    return {
        "items": results,
        "meta": {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "universe_size": len(universe),
            "window_days": window_days,
            "events_found": len(results),
            "errors": errors,
            "note": (
                "Earnings dates from Yahoo Finance quoteSummary (consensus EPS + surprise history). "
                f"Showing names reporting in the next {window_days} calendar days."
            ),
        },
    }
