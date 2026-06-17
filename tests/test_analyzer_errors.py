"""analyze_market must degrade gracefully — return an Analysis with `error`, never raise."""

from __future__ import annotations

from conftest import make_market
from research import analyzer


def test_analyze_market_never_raises(monkeypatch) -> None:
    analyzer.reset_openai_exhausted()

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(analyzer, "_complete", boom)
    a = analyzer.analyze_market(make_market())
    assert a.error is not None
    assert "network down" in a.error
    assert a.claude_prob is None  # no invented estimate on failure


def test_quota_error_latches_and_resets(monkeypatch) -> None:
    analyzer.reset_openai_exhausted()

    def quota(*a, **k):
        raise RuntimeError("Error code: 429 - insufficient_quota")

    monkeypatch.setattr(analyzer, "_complete", quota)
    a = analyzer.analyze_market(make_market())
    assert a.error and "anthropic" in a.error.lower()
    assert analyzer.openai_exhausted() is True

    analyzer.reset_openai_exhausted()
    assert analyzer.openai_exhausted() is False
