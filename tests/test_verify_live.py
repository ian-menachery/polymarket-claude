"""verify_live.py must print the spend/parse breakdown offline (no real LLM call)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import verify_live  # noqa: E402

from conftest import make_market  # noqa: E402
from research.models import Analysis  # noqa: E402


def test_prints_cost_breakdown(temp_db, monkeypatch, capsys) -> None:
    temp_db.upsert_markets([make_market(id="mkt-1", market_prob=0.5)])
    monkeypatch.setattr(verify_live.analyzer, "analyze_market", lambda m: Analysis(
        market_id=m.id, model="claude-sonnet-4-6", claude_prob=0.62,
        input_tokens=1500, output_tokens=700, cache_read_input_tokens=0,
    ))
    monkeypatch.setattr(sys, "argv", ["verify_live.py", "mkt-1"])

    verify_live.main()  # must not raise

    out = capsys.readouterr().out
    assert "claude_prob   : 0.62" in out
    assert "cost_usd" in out
    assert "no cache reads" in out  # cache_read == 0 path


def test_errors_when_no_markets(temp_db, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["verify_live.py"])
    try:
        verify_live.main()
        raise AssertionError("expected SystemExit on empty DB")
    except SystemExit as e:
        assert "refresh" in str(e)
