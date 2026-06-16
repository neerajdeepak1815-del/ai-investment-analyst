"""
Market regime indicator — Fama-French / AQR factor regime detection.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Optional

from app.opportunities.universe import SECTOR_ETFS
from app.opportunities.yahoo_data import fetch_history_closes, trading_day_return, yahoo_symbol

logger = logging.getLogger(__name__)


def _sma(closes: list[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _pct_above_200ma(universe: list[str]) -> tuple[Optional[float], int, int]:
    above = 0
    total = 0

    def _check(ticker: str) -> Optional[bool]:
        closes = fetch_history_closes(yahoo_symbol(ticker), days=400)
        if closes is None or len(closes) < 200:
            return None
        ma200 = sum(closes[-200:]) / 200.0
        return closes[-1] > ma200

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_check, t) for t in universe]
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r is not None:
                    total += 1
                    if r:
                        above += 1
            except Exception:
                pass

    if total == 0:
        return None, 0, len(universe)
    return round(above / total * 100, 1), above, total


def _sector_performance() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def _calc(symbol: str) -> Optional[dict[str, Any]]:
        closes = fetch_history_closes(symbol, days=90)
        if closes is None or len(closes) < 22:
            return None
        ret_1m = trading_day_return(closes, 21)
        ret_3m = trading_day_return(closes, 63)
        if ret_1m is None:
            return None
        return {
            "symbol": symbol,
            "sector": SECTOR_ETFS.get(symbol, symbol),
            "ret_1m": round(ret_1m, 2),
            "ret_3m": round(ret_3m, 2) if ret_3m is not None else None,
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_calc, s): s for s in SECTOR_ETFS}
        for fut in as_completed(futures):
            r = fut.result()
            if r is not None:
                results.append(r)

    results.sort(key=lambda r: r["ret_1m"], reverse=True)
    return results


def _credit_label(xlf_spy_spread: Optional[float]) -> str:
    if xlf_spy_spread is None:
        return "unknown"
    if xlf_spy_spread > 1.0:
        return "financials leading (risk-on)"
    if xlf_spy_spread < -1.0:
        return "financials lagging (risk-off)"
    return "neutral"


def scan_regime(universe: list[str]) -> dict[str, Any]:
    warnings: list[str] = []

    spy_closes = fetch_history_closes("SPY", days=400)
    if spy_closes is None:
        warnings.append("SPY price history unavailable — regime signals degraded.")

    spy_current = spy_closes[-1] if spy_closes else None
    spy_ma50 = _sma(spy_closes, 50) if spy_closes else None
    spy_ma200 = _sma(spy_closes, 200) if spy_closes else None
    spy_above_200 = (spy_current > spy_ma200) if spy_current and spy_ma200 else None

    cross_signal = None
    if spy_ma50 is not None and spy_ma200 is not None:
        cross_signal = "golden_cross" if spy_ma50 > spy_ma200 else "death_cross"

    trend = "sideways"
    if spy_closes and len(spy_closes) >= 21:
        ret_20d = trading_day_return(spy_closes, 20)
        if ret_20d is not None:
            if ret_20d > 2.0:
                trend = "uptrend"
            elif ret_20d < -2.0:
                trend = "downtrend"

    vix_closes = fetch_history_closes("^VIX", days=60)
    if vix_closes is None:
        warnings.append("VIX data unavailable.")
    vix_current = round(vix_closes[-1], 2) if vix_closes else None
    vix_label = "unknown"
    if vix_current is not None:
        if vix_current < 15:
            vix_label = "low"
        elif vix_current <= 25:
            vix_label = "normal"
        elif vix_current <= 35:
            vix_label = "elevated"
        else:
            vix_label = "panic"

    breadth, breadth_above, breadth_total = _pct_above_200ma(universe)
    if breadth_total < len(universe) * 0.5:
        warnings.append(f"Breadth computed on {breadth_total}/{len(universe)} names only (partial data).")

    xlf_closes = fetch_history_closes("XLF", days=60)
    credit_spread = None
    credit_label = "unknown"
    if xlf_closes and spy_closes and len(xlf_closes) >= 22 and len(spy_closes) >= 22:
        xlf_ret = trading_day_return(xlf_closes, 21)
        spy_ret = trading_day_return(spy_closes, 21)
        if xlf_ret is not None and spy_ret is not None:
            credit_spread = round(xlf_ret - spy_ret, 2)
            credit_label = _credit_label(credit_spread)

    sectors = _sector_performance()
    if len(sectors) < len(SECTOR_ETFS) // 2:
        warnings.append("Sector ETF data partially unavailable.")

    bull_signals = bear_signals = 0
    if spy_above_200 is True:
        bull_signals += 2
    elif spy_above_200 is False:
        bear_signals += 2
    if cross_signal == "golden_cross":
        bull_signals += 1
    elif cross_signal == "death_cross":
        bear_signals += 1
    if vix_current is not None:
        if vix_current < 20:
            bull_signals += 1
        elif vix_current > 30:
            bear_signals += 2
        elif vix_current > 25:
            bear_signals += 1
    if breadth is not None:
        if breadth > 60:
            bull_signals += 1
        elif breadth < 40:
            bear_signals += 1
    if trend == "uptrend":
        bull_signals += 1
    elif trend == "downtrend":
        bear_signals += 1
    if credit_spread is not None:
        if credit_spread > 1.0:
            bull_signals += 1
        elif credit_spread < -1.0:
            bear_signals += 1

    if bull_signals >= 4 and bear_signals <= 1:
        regime = "bull"
        regime_label = "BULL MARKET — MOMENTUM FAVORED"
        favored = "Momentum"
        overweight = "Wood (growth) and Ackman (quality momentum) lenses"
        underweight = "Burry (deep value) — limited upside in strong trends"
    elif bear_signals >= 4 and bull_signals <= 1:
        regime = "bear"
        regime_label = "BEAR MARKET — DEFENSIVE FAVORED"
        favored = "Defensive / Value"
        overweight = "Burry (balance sheet) and Buffett (quality moat) lenses"
        underweight = "Wood (growth) — high-beta names vulnerable in downturns"
    else:
        regime = "transition"
        regime_label = "TRANSITIONING — QUALITY FAVORED"
        favored = "Quality"
        overweight = "Buffett (moat) and Institutional (earnings quality) lenses"
        underweight = "Pure momentum — elevated crash risk in transitions"

    return {
        "regime": regime,
        "regime_label": regime_label,
        "favored_strategy": favored,
        "overweight": overweight,
        "underweight": underweight,
        "spy_current": round(spy_current, 2) if spy_current else None,
        "spy_ma50": round(spy_ma50, 2) if spy_ma50 else None,
        "spy_ma200": round(spy_ma200, 2) if spy_ma200 else None,
        "spy_above_200ma": spy_above_200,
        "cross_signal": cross_signal,
        "trend": trend,
        "vix_current": vix_current,
        "vix_label": vix_label,
        "breadth_pct": breadth,
        "breadth_above": breadth_above,
        "breadth_total": breadth_total,
        "credit_spread_1m": credit_spread,
        "credit_label": credit_label,
        "sectors": sectors,
        "bull_signals": bull_signals,
        "bear_signals": bear_signals,
        "meta": {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "universe_size": len(universe),
            "warnings": warnings,
            "methodology": (
                "SPY vs 200-day MA, 50/200 cross, VIX level, % of universe above 200MA, "
                "20-day SPY trend, XLF vs SPY 1-month relative return. Trading-day returns on adjusted prices."
            ),
        },
    }
