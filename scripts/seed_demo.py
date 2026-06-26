"""Seed synthetic DEMO data so the Leaderboard / Performance / Calibration views populate
without any API spend or waiting for real markets to resolve.

Everything written is clearly labeled ("[DEMO]" questions, "demo-*" ids) and is meant for a
THROWAWAY database — point it at a separate file so your real data/polymarket.db stays clean:

    RESEARCH_DB_PATH=data/demo.db PYTHONPATH=src python scripts/seed_demo.py
    RESEARCH_DB_PATH=data/demo.db make run        # screenshots; then delete data/demo.db

Writes only through the sanctioned ``research.db`` API (no raw SQL); ``db`` resolves
RESEARCH_DB_PATH at call time, so the env var alone targets the demo DB. Deterministic via a
fixed RNG seed. The synthetic models are made slightly *overconfident* so temperature-scaling
calibration visibly pulls estimates toward 0.5 (T > 1) instead of being a no-op.

Run:  RESEARCH_DB_PATH=… PYTHONPATH=src python scripts/seed_demo.py [n_per_model] [n_signals] [seed]
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone

from research import db
from research.models import Analysis, Market, Signal

DEMO_MODELS = ["gpt-5.5", "claude-sonnet-4-6"]


def _utc_days_ago(days: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _seed_analyses(rng: random.Random, model: str, n: int) -> None:
    """Insert ``n`` resolved analyses for ``model``, spread across the 10 reliability bins.

    Outcomes are drawn from a deliberately *overconfident* true rate (pulled toward 0.5), so the
    reliability curve bends and ``fit_temperature`` returns T > 1 — calibration does real work.
    """
    for i in range(n):
        prob = (i % 10) / 10.0 + 0.05  # bin midpoints 0.05 .. 0.95 (even fill)
        true_rate = 0.5 + (prob - 0.5) * 0.7  # model is overconfident vs reality
        outcome = rng.random() < true_rate
        mid = round(rng.uniform(0.25, 0.75), 2)  # crowd mid at analysis time
        market_id = f"demo-{model}-{i}"
        db.upsert_markets([Market(
            id=market_id,
            slug=f"demo-{model}-{i}",
            question=f"[DEMO] Will synthetic event {i} for {model} happen?",
            market_prob=mid,
            volume_24h=float(rng.randint(20_000, 500_000)),
            volume_total=float(rng.randint(100_000, 2_000_000)),
            liquidity=float(rng.randint(10_000, 200_000)),
            end_date=_utc_days_ago(rng.uniform(1, 30)),
            tags=["demo"],
            description="Synthetic demo market — not a real Polymarket/Kalshi market.",
        )])
        db.save_analysis(Analysis(
            market_id=market_id,
            model=model,
            claude_prob=prob,
            market_prob_at_analysis=mid,
            confidence=rng.choice(["low", "medium", "high"]),
            summary=f"[DEMO] synthetic analysis #{i}",
        ))
        db.mark_resolution(market_id, outcome)


def _seed_signals(rng: random.Random, n: int) -> int:
    """Insert ``n`` settled forward signals (mixed wins/losses) for the Performance view.

    P&L uses the same modeled-VWAP-fill formula as ``scanner.sweep_resolutions``.
    """
    settled = 0
    for i in range(n):
        model = rng.choice(DEMO_MODELS)
        side = rng.choice(["YES", "NO"])
        price_paid = round(rng.uniform(0.2, 0.8), 2)
        fill_shares = float(rng.randint(40, 200))
        market_id = f"demo-sig-{i}"
        db.upsert_markets([Market(
            id=market_id,
            slug=f"demo-sig-{i}",
            question=f"[DEMO] Signal market {i}",
            market_prob=price_paid,
            volume_24h=float(rng.randint(20_000, 500_000)),
            end_date=_utc_days_ago(rng.uniform(1, 20)),
            tags=["demo"],
            description="Synthetic demo signal market.",
        )])
        sig_id = db.save_signal(Signal(
            market_id=market_id,
            question=f"[DEMO] Signal market {i}",
            model=model,
            side=side,
            calibrated_prob=round(rng.uniform(0.55, 0.9), 2),
            market_prob=price_paid,
            price_paid=price_paid,
            ev=round(rng.uniform(0.02, 0.2), 3),
            ev_pct=round(rng.uniform(0.05, 0.4), 3),
            fill_shares=fill_shares,
            target_position_usd=50.0,
            days_to_close=rng.uniform(5, 30),
        ))
        # Win the chosen side ~55% of the time so the equity curve trends up but isn't flat.
        outcome_yes = rng.random() < (0.55 if side == "YES" else 0.45)
        won = (side == "YES") == outcome_yes
        pnl = fill_shares * (1.0 - price_paid) if won else -fill_shares * price_paid
        db.resolve_signal(sig_id, outcome_yes, round(pnl, 2))
        settled += 1
    return settled


def seed(n_per_model: int = 60, n_signals: int = 24, seed_value: int = 7) -> dict:
    """Populate the configured DB with demo analyses + settled signals. Returns counts."""
    rng = random.Random(seed_value)
    db.init_db()
    for model in DEMO_MODELS:
        _seed_analyses(rng, model, n_per_model)
    settled = _seed_signals(rng, n_signals)
    return {
        "models": DEMO_MODELS,
        "analyses_per_model": n_per_model,
        "total_analyses": n_per_model * len(DEMO_MODELS),
        "settled_signals": settled,
    }


def main() -> None:
    n_per_model = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    n_signals = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    seed_value = int(sys.argv[3]) if len(sys.argv) > 3 else 7

    target = os.getenv("RESEARCH_DB_PATH", "data/polymarket.db (default)")
    if "polymarket.db (default)" in target:
        print("WARNING: RESEARCH_DB_PATH not set — seeding the DEFAULT db. Set it to a demo file,")
        print("         e.g. RESEARCH_DB_PATH=data/demo.db, to keep real data clean. Ctrl-C to abort.")

    counts = seed(n_per_model, n_signals, seed_value)
    print("=" * 70)
    print("SEEDED DEMO DATA (synthetic - clearly labeled '[DEMO]')")
    print("=" * 70)
    print(f"db                 : {os.getenv('RESEARCH_DB_PATH', 'data/polymarket.db')}")
    print(f"models             : {', '.join(counts['models'])}")
    print(f"resolved analyses  : {counts['total_analyses']} ({counts['analyses_per_model']}/model)")
    print(f"settled signals    : {counts['settled_signals']}")
    print("-" * 70)
    print("Now: RESEARCH_DB_PATH=<same db> make run  -> Leaderboard / Performance / Calibration populate.")
    print("Delete the demo db when done; it's synthetic and must never feed real calibration.")


if __name__ == "__main__":
    main()
