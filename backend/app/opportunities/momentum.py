"""
Momentum screener — Jegadeesh & Titman (1993) factor implementation.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

from app.opportunities.universe import ticker_meta
from app.opportunities.yahoo_data import (
    compute_rsi_wilder,
    fetch_history_closes,
    percentile_rank_score,
    trading_day_return,
    yahoo_symbol,
)

logger = logging.getLogger(__name__)


def _analyze_ticker(ticker: str, closes: list[float]) -> Optional[dict[str, Any]]:
    if len(closes) < 63:
        return None

    current = closes[-1]
    ret_1m = trading_day_return(closes, 21)
    ret_6m = trading_day_return(closes, 126)
    ret_12m = trading_day_return(closes, 252)

    # Momentum crash filter: skip if last month negative
    if ret_1m is not None and ret_1m < 0:
        return None

    lookback = min(252, len(closes))
    high_52w = max(closes[-lookback:])
    dist_high = (current / high_52w - 1.0) * 100.0 if high_52w > 0 else None

    rsi_val = compute_rsi_wilder(closes)
    return {
        "ticker": ticker,
        "current_price": round(current, 2),
        "ret_1m": round(ret_1m, 2) if ret_1m is not None else None,
        "ret_6m": round(ret_6m, 2) if ret_6m is not None else None,
        "ret_12m": round(ret_12m, 2) if ret_12m is not None else None,
        "ret_12m_partial": len(closes) < 253,
        "high_52w": round(high_52w, 2),
        "dist_high_pct": round(dist_high, 2) if dist_high is not None else None,
        "rsi": round(rsi_val, 1) if rsi_val is not None else None,
        "sparkline": [round(c, 2) for c in closes[-60:]],
        "_closes": closes,
    }


def _fetch_with_volume(ticker: str) -> Optional[dict[str, Any]]:
    sym = yahoo_symbol(ticker)
    closes: Optional[list[float]] = None
    volumes: Optional[list[float]] = None

    try:
        import yfinance as yf
        from datetime import timedelta

        end = datetime.now()
        start = end - timedelta(days=400)
        hist = yf.Ticker(sym).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
        )
        if hist is not None and len(hist) >= 63:
            closes = [float(x) for x in hist["Close"].tolist() if x == x]
            volumes = [float(x) for x in hist["Volume"].tolist() if x == x]
    except Exception as exc:
        logger.debug("yfinance momentum %s: %s", sym, exc)

    if closes is None or len(closes) < 63:
        closes = fetch_history_closes(sym, days=400)
        volumes = None

    if closes is None or len(closes) < 63:
        return None

    base = _analyze_ticker(ticker, closes)
    if base is None:
        return None

    meta = ticker_meta(ticker)
    base["name"] = meta["name"]
    base["sector"] = meta["sector"]

    vol_ratio = None
    vol_trend = "unknown"
    if volumes and len(volumes) >= 50:
        vol_20 = sum(volumes[-20:]) / 20.0
        vol_50 = sum(volumes[-50:]) / 50.0
        if vol_50 > 0:
            vol_ratio = vol_20 / vol_50
            if vol_ratio > 1.05:
                vol_trend = "increasing"
            elif vol_ratio < 0.95:
                vol_trend = "decreasing"
            else:
                vol_trend = "stable"

    base["vol_ratio"] = round(vol_ratio, 3) if vol_ratio is not None else None
    base["vol_trend"] = vol_trend
    base.pop("_closes", None)
    return base


def scan_momentum(universe: list[str], top_n: int = 5) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    screened = len(universe)
    filtered_crash = 0
    data_errors = 0

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_with_volume, t): t for t in universe}
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                row = fut.result()
                if row is None:
                    closes = fetch_history_closes(yahoo_symbol(ticker), days=400)
                    if closes and len(closes) >= 63:
                        r1 = trading_day_return(closes, 21)
                        if r1 is not None and r1 < 0:
                            filtered_crash += 1
                        else:
                            data_errors += 1
                    else:
                        data_errors += 1
                    continue
                results.append(row)
            except Exception as exc:
                data_errors += 1
                logger.debug("momentum %s: %s", ticker, exc)

    if not results:
        return {
            "items": [],
            "meta": {
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "universe_size": len(universe),
                "screened": screened,
                "passed_filter": 0,
                "filtered_momentum_crash": filtered_crash,
                "data_errors": data_errors,
                "note": "No momentum candidates passed filters. Negative 1-month return excludes names (momentum crash filter).",
            },
        }

    ret6 = [r["ret_6m"] if r["ret_6m"] is not None else -999.0 for r in results]
    ret12 = [r["ret_12m"] if r["ret_12m"] is not None else -999.0 for r in results]
    vols = [r["vol_ratio"] if r["vol_ratio"] is not None else 1.0 for r in results]

    for i, r in enumerate(results):
        score = 0.0
        if r["ret_6m"] is not None:
            score += percentile_rank_score(ret6, i, 30.0)
        if r["ret_12m"] is not None:
            score += percentile_rank_score(ret12, i, 25.0)
        score += percentile_rank_score(vols, i, 20.0)

        rsi = r.get("rsi")
        if rsi is not None:
            if 50 <= rsi <= 70:
                score += 15.0
            elif 40 <= rsi < 50 or 70 < rsi <= 80:
                score += 7.0

        dist = r.get("dist_high_pct")
        if dist is not None and dist >= -15.0:
            score += 10.0
        elif dist is not None and dist >= -25.0:
            score += 4.0

        r["momentum_score"] = round(score, 1)

    results.sort(key=lambda r: r["momentum_score"], reverse=True)
    top = results[:top_n]

    return {
        "items": top,
        "meta": {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "universe_size": len(universe),
            "screened": screened,
            "passed_filter": len(results),
            "filtered_momentum_crash": filtered_crash,
            "data_errors": data_errors,
            "top_n": top_n,
            "methodology": (
                "6M/12M returns use 126/252 trading days on adjusted closes. "
                "1M crash filter excludes negative 21-day return. "
                "Composite score: percentile ranks (6M 30%, 12M 25%, volume 20%) + RSI band + proximity to 52W high."
            ),
        },
    }
