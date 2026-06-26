"""seed_demo.py must populate the Leaderboard / Performance / Calibration data offline."""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ isn't a package on the path; add it so we can import the seed module.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import seed_demo  # noqa: E402

from research import calibration, performance  # noqa: E402


def test_seed_populates_all_views(temp_db) -> None:
    counts = seed_demo.seed(n_per_model=60, n_signals=10, seed_value=1)
    assert counts["total_analyses"] == 120

    # Leaderboard: both demo models present and past the calibration threshold (n >= MIN_N=50).
    board = {e["model"]: e for e in calibration.model_leaderboard()}
    assert set(seed_demo.DEMO_MODELS) <= set(board)
    assert all(board[m]["calibrated"] for m in seed_demo.DEMO_MODELS)

    # Calibration: the overconfident synthetic data makes temperature scaling do real work (T > 1).
    recals = calibration.build_recalibrators()
    assert any(r.calibrated and r.temperature > 1.0 for r in recals.values())

    # Performance: settled signals feed the equity curve.
    perf = performance.report()
    assert perf["settled"] == 10
    assert perf["equity_curve"]
