"""Tests for the exchange dispatcher and Kalshi resolution mapping (no network)."""

from __future__ import annotations

import pytest

from conftest import make_market

from research import exchanges, kalshi


class TestFetchActiveDispatch:
    def _patch(self, monkeypatch):
        monkeypatch.setattr(exchanges.polymarket, "fetch_all_active",
                            lambda max_markets: ["poly"] * 1)
        monkeypatch.setattr(exchanges.kalshi, "fetch_all_active",
                            lambda max_markets: ["kalshi"] * 1)

    def test_default_is_polymarket(self, monkeypatch):
        self._patch(monkeypatch)
        monkeypatch.delenv("EXCHANGE", raising=False)
        assert exchanges.fetch_active(10) == ["poly"]

    def test_kalshi(self, monkeypatch):
        self._patch(monkeypatch)
        monkeypatch.setenv("EXCHANGE", "kalshi")
        assert exchanges.fetch_active(10) == ["kalshi"]

    def test_both_concatenates(self, monkeypatch):
        self._patch(monkeypatch)
        monkeypatch.setenv("EXCHANGE", "both")
        assert exchanges.fetch_active(10) == ["poly", "kalshi"]


class TestFetchResolutionDispatch:
    def test_routes_by_market_exchange(self, monkeypatch):
        monkeypatch.setattr(exchanges.polymarket, "fetch_resolution", lambda mid: ("poly", mid))
        monkeypatch.setattr(exchanges.kalshi, "fetch_resolution", lambda mid: ("kalshi", mid))
        poly_m = make_market(id="0x1", exchange="polymarket")
        kalshi_m = make_market(id="TICKER-1", exchange="kalshi")
        assert exchanges.fetch_resolution(poly_m) == ("poly", "0x1")
        assert exchanges.fetch_resolution(kalshi_m) == ("kalshi", "TICKER-1")


class _FakeClient:
    """Minimal KalshiClient stand-in: context manager whose .get returns a fixed body."""

    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, path, **params):
        return self._body


class TestKalshiResolutionMapping:
    @pytest.mark.parametrize(
        "result,expected",
        [("yes", True), ("YES", True), ("no", False), ("", None), ("void", None), (None, None)],
    )
    def test_result_maps_to_bool(self, monkeypatch, result, expected):
        body = {"market": {"result": result}}
        monkeypatch.setattr(kalshi, "KalshiClient", lambda *a, **k: _FakeClient(body))
        assert kalshi.fetch_resolution("TICKER-1") is expected

    def test_missing_market_is_none(self, monkeypatch):
        monkeypatch.setattr(kalshi, "KalshiClient", lambda *a, **k: _FakeClient({}))
        assert kalshi.fetch_resolution("TICKER-1") is None
