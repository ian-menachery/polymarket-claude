"""App routes whose handlers call scanner/exchanges/calibration/performance — mocked, no network."""

from __future__ import annotations

from conftest import make_market

from research import analyzer, calibration, db, exchanges, performance, scanner
from research.models import Analysis, ScanResult


def test_scan_route_returns_result_list(client, monkeypatch) -> None:
    m = make_market(market_prob=0.5)
    sr = ScanResult(
        market=m,
        analysis=Analysis(market_id=m.id, claude_prob=0.7, model="x"),
        calibrated_prob=0.7, side="YES", ev=0.1, annualized_ev=0.5,
    )
    monkeypatch.setattr(scanner, "scan", lambda req: [sr])
    r = client.post("/api/scan", json={"max_markets": 5})
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body, list) and body[0]["market"]["id"] == m.id


def test_scan_estimate_route(client, monkeypatch) -> None:
    monkeypatch.setattr(scanner, "estimate_scan",
                        lambda req: {"fresh_analyses": 3, "estimated_cost_usd": 0.1})
    r = client.post("/api/scan/estimate", json={"max_markets": 5})
    assert r.status_code == 200
    assert r.get_json()["fresh_analyses"] == 3


def test_leaderboard_route(client, monkeypatch) -> None:
    monkeypatch.setattr(calibration, "model_leaderboard", lambda: [{"model": "x", "brier": 0.1}])
    r = client.get("/api/leaderboard")
    assert r.status_code == 200
    assert r.get_json()[0]["model"] == "x"


def test_performance_route(client, monkeypatch) -> None:
    monkeypatch.setattr(performance, "report", lambda: {"settled": 2, "equity_curve": []})
    r = client.get("/api/performance")
    assert r.status_code == 200
    assert r.get_json()["settled"] == 2


def test_signals_route_shape(client) -> None:
    r = client.get("/api/signals")
    assert r.status_code == 200
    body = r.get_json()
    assert "summary" in body and "signals" in body


def test_refresh_route(client, monkeypatch) -> None:
    monkeypatch.setattr(exchanges, "fetch_active", lambda max_markets: [make_market(market_prob=0.5)])
    monkeypatch.setattr(scanner, "sweep_resolutions", lambda: 0)
    r = client.post("/api/markets/refresh")
    assert r.status_code == 200
    assert r.get_json()["count"] == 1


def test_refresh_route_surfaces_upstream_error(client, monkeypatch) -> None:
    def boom(max_markets):
        raise RuntimeError("gamma down")

    monkeypatch.setattr(exchanges, "fetch_active", boom)
    r = client.post("/api/markets/refresh")
    assert r.status_code == 502
    assert "gamma down" in r.get_json()["error"]


def test_analyze_route_success(client, monkeypatch) -> None:
    db.upsert_markets([make_market(market_prob=0.5)])  # id defaults to "mkt-1"
    monkeypatch.setattr(analyzer, "analyze_market",
                        lambda m: Analysis(market_id=m.id, claude_prob=0.8, model="x"))
    r = client.post("/api/markets/mkt-1/analyze")
    assert r.status_code == 200
    assert r.get_json()["claude_prob"] == 0.8


def test_analyze_route_surfaces_error(client, monkeypatch) -> None:
    db.upsert_markets([make_market(market_prob=0.5)])
    monkeypatch.setattr(analyzer, "analyze_market",
                        lambda m: Analysis(market_id=m.id, model="x", error="boom"))
    r = client.post("/api/markets/mkt-1/analyze")
    assert r.status_code == 502
    assert r.get_json()["error"] == "boom"
