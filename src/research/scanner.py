"""Batch EV scanner — fetch markets, analyze, rank by (uncalibrated) annualized EV.

Sequential (no asyncio); a ``time.sleep`` between Claude calls keeps us within
rate limits. Markets analyzed within ``max_age_hours`` reuse their stored analysis
instead of paying for a fresh call.

IMPORTANT: the EV figures here use the market **mid** price and Claude's
**uncalibrated** estimate. They are directional only until Phase 3 (calibration)
and Phase 3.5 (executable bid/ask). Treat the ranking as "where to look," not
"guaranteed +EV."
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from research import analyzer, calibration, db, polymarket
from research.models import Market, ScanRequest, ScanResult


def _days_to_close(market: Market) -> float | None:
    if market.end_date is None:
        return None
    return (market.end_date - datetime.now(timezone.utc)).total_seconds() / 86400.0


def _ev_fields(
    market: Market, prob: float | None, bid: float | None, ask: float | None, min_days: float
) -> dict:
    """EV on the favorable side priced at the *executable* CLOB top-of-book.

    Side is the directional intent (calibrated ``prob`` vs the market mid). The cost
    is then the price you'd actually fill at: BUY YES at the ask, or bet NO at
    ``1 - bid`` (buying NO == selling YES at the bid, by no-arbitrage). ``ev`` can be
    negative once the spread is included — those get dropped by the min_divergence
    gate. Annualized EV is None below the days floor.
    """
    mp = market.market_prob
    dtc = _days_to_close(market)
    blank = {"side": None, "ev": None, "ev_pct": None, "kelly": None,
             "annualized_ev": None, "days_to_close": dtc,
             "best_bid": bid, "best_ask": ask, "price_paid": None}
    if mp is None or prob is None:
        return blank

    side = "YES" if prob > mp else "NO"
    if side == "YES":
        if ask is None:
            return blank  # can't buy YES — skip
        price_paid, ev = ask, prob - ask
    else:
        if bid is None:
            return blank  # can't establish NO — skip
        price_paid, ev = 1.0 - bid, bid - prob
    if not (0.0 < price_paid < 1.0):
        return {**blank, "side": side}

    ev_pct = ev / price_paid
    kelly = ev / (1.0 - price_paid)
    annualized = ev_pct * 365.0 / dtc if (dtc is not None and dtc >= min_days) else None
    return {"side": side, "ev": ev, "ev_pct": ev_pct, "kelly": kelly,
            "annualized_ev": annualized, "days_to_close": dtc,
            "best_bid": bid, "best_ask": ask, "price_paid": price_paid}


def scan(req: ScanRequest) -> list[ScanResult]:
    """Run a batch EV scan and return results sorted by annualized EV (desc)."""
    recals = calibration.build_recalibrators()  # one per model; fit once, applied per market
    markets = polymarket.fetch_all_active(max_markets=req.max_markets)
    db.upsert_markets(markets)  # persist fetched markets (also satisfies the analyses FK)

    # Cheap pre-filters first — they bound how many paid Claude calls we make.
    def passes_pre(m: Market) -> bool:
        dtc = _days_to_close(m)
        return (
            (m.volume_24h or 0.0) >= req.min_volume_24h
            and (m.liquidity or 0.0) >= req.min_liquidity
            and dtc is not None
            and dtc >= req.min_days_to_close
            and (req.category is None or req.category in m.tags)
        )

    candidates = [m for m in markets if passes_pre(m)]
    delay = float(os.getenv("ANALYSIS_DELAY_SECONDS", "1.5"))
    results: list[ScanResult] = []

    for m in candidates:
        age = db.get_analysis_age_hours(m.id)
        if age is not None and age <= req.max_age_hours:
            analysis = db.get_latest_analysis(m.id)  # reuse recent — no API cost
        else:
            analysis = analyzer.analyze_market(m)
            if analysis.error:
                continue  # don't persist failures; skip
            db.save_analysis(analysis)
            time.sleep(delay)

        if analysis is None or analysis.claude_prob is None:
            continue

        recal = recals.get(analysis.model) or calibration.identity_recalibrator(analysis.model)
        calibrated_p = recal.apply(analysis.claude_prob)

        bid, ask = (None, None)
        if m.yes_token_id:
            try:
                bid, ask = polymarket.fetch_best_bid_ask(m.yes_token_id)
            except Exception:  # noqa: BLE001 — CLOB hiccup shouldn't kill the scan
                bid, ask = (None, None)

        ev = _ev_fields(m, calibrated_p, bid, ask, req.min_days_to_close)
        if ev["side"] is None:  # no executable price on the needed side — skip
            continue
        if ev["ev"] is None or ev["ev"] < req.min_divergence:  # gate on EXECUTABLE edge
            continue
        if ev["annualized_ev"] is None:  # failed the days floor (defensive)
            continue
        results.append(ScanResult(market=m, analysis=analysis, calibrated_prob=calibrated_p, **ev))

    results.sort(key=lambda r: r.annualized_ev or -1.0, reverse=True)
    return results
