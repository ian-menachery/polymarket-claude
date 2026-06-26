"""Scheduler run_once + history, fully mocked (no scan, no network, no timers)."""

from __future__ import annotations

from research import scanner, scheduler


def test_run_once_records_cost_and_aggregates(temp_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCAN_LOG_PATH", str(tmp_path / "scan_log.jsonl"))
    monkeypatch.setattr(scanner, "scan_with_stats",
                        lambda req: ([], {"llm_calls": 4, "fresh_analyses": 4,
                                          "refutations": 0, "cost_usd": 1.23}))
    monkeypatch.setattr(scanner, "persist_signals", lambda results: 0)
    monkeypatch.setattr(scanner, "emit_alerts", lambda results: 0)
    monkeypatch.setattr(scanner, "sweep_resolutions", lambda: 2)

    rec = scheduler.run_once()
    assert rec["llm_calls"] == 4
    assert rec["cost_usd"] == 1.23
    assert rec["resolutions_captured"] == 2
    assert rec["errors"] == []

    hist = scheduler.history()
    assert hist["total_runs"] == 1
    assert hist["total_llm_calls"] == 4
    assert hist["total_cost_usd"] == 1.23


def test_run_once_isolates_scan_failure_from_sweep(temp_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCAN_LOG_PATH", str(tmp_path / "log.jsonl"))

    def boom(req):
        raise RuntimeError("scan boom")

    monkeypatch.setattr(scanner, "scan_with_stats", boom)
    monkeypatch.setattr(scanner, "sweep_resolutions", lambda: 5)
    rec = scheduler.run_once()
    assert any("scan boom" in e for e in rec["errors"])
    assert rec["resolutions_captured"] == 5  # sweep still runs despite the scan failing


def test_history_missing_file_is_empty(temp_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCAN_LOG_PATH", str(tmp_path / "nope.jsonl"))
    h = scheduler.history()
    assert h["total_runs"] == 0
    assert h["total_cost_usd"] == 0.0
    assert h["last_runs"] == []


def test_history_skips_malformed_lines(temp_db, monkeypatch, tmp_path) -> None:
    p = tmp_path / "log.jsonl"
    p.write_text(
        '{"edges_found": 3, "markets_scanned": 5, "cost_usd": 0.5, "llm_calls": 2}\n'
        "}{ not json\n"
        "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCAN_LOG_PATH", str(p))
    h = scheduler.history()
    assert h["total_runs"] == 1  # malformed/blank lines skipped
    assert h["total_cost_usd"] == 0.5
    assert h["avg_edges_per_run"] == 3.0
