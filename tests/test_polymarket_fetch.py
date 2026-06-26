"""Polymarket resolution detection + fetch_resolution, mocked (no network)."""

from __future__ import annotations

from research import polymarket


class TestDetectResolution:
    def test_yes_won(self) -> None:
        raw = {"closed": True, "outcomePrices": '["0.995","0.005"]', "outcomes": '["Yes","No"]'}
        assert polymarket._detect_resolution(raw) is True

    def test_no_won(self) -> None:
        raw = {"closed": True, "outcomePrices": '["0.01","0.99"]', "outcomes": '["Yes","No"]'}
        assert polymarket._detect_resolution(raw) is False

    def test_open_market_is_none(self) -> None:
        assert polymarket._detect_resolution({"closed": False}) is None

    def test_undecided_prices_is_none(self) -> None:
        raw = {"closed": True, "outcomePrices": '["0.6","0.4"]', "outcomes": '["Yes","No"]'}
        assert polymarket._detect_resolution(raw) is None


class _FakeGamma:
    """GammaClient stand-in: context manager whose .get returns a fixed page."""

    def __init__(self, page):
        self._page = page

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, path, **params):
        return self._page


def test_fetch_resolution_matches_by_id(monkeypatch) -> None:
    page = [{"id": "123", "closed": True,
             "outcomePrices": '["0.99","0.01"]', "outcomes": '["Yes","No"]'}]
    monkeypatch.setattr(polymarket, "GammaClient", lambda *a, **k: _FakeGamma(page))
    assert polymarket.fetch_resolution("123") is True


def test_fetch_resolution_not_found_is_none(monkeypatch) -> None:
    monkeypatch.setattr(polymarket, "GammaClient", lambda *a, **k: _FakeGamma([]))
    assert polymarket.fetch_resolution("123") is None
