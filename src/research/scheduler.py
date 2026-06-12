"""Background auto-scan scheduler (stdlib threading.Timer — no APScheduler).

When ``SCAN_INTERVAL_HOURS`` is set (> 0), runs a full ``scanner.scan()`` plus a
``scanner.sweep_resolutions()`` on that interval, appending one JSON line per run to
``data/scan_log.jsonl``. This drives the calibration flywheel (accumulate analyses,
capture resolutions) without manual refreshes.

Started only from ``app.py``'s ``__main__`` block — never on import — so importing the
app for tests/scripts/test_client never spawns live scans. Each run spends LLM budget
(bounded by ``MAX_SCAN_MARKETS``) and uses the configured ``LLM_PROVIDER``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from research import db, scanner
from research.models import ScanRequest

_log = logging.getLogger(__name__)
_timer: threading.Timer | None = None


def _scan_log_path() -> Path:
    override = os.getenv("SCAN_LOG_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "data" / "scan_log.jsonl"


def _build_request() -> ScanRequest:
    # Defaults for the gates; no refutation on autoscan (refute_top=0) to bound cost.
    return ScanRequest(max_markets=int(os.getenv("MAX_SCAN_MARKETS", "100")))


def run_once() -> dict:
    """Run one scan + resolution sweep, append a JSON log line, return the record.

    Never raises: scan and sweep are independently guarded so one failing neither
    skips the other nor kills the scheduler.
    """
    errors: list[str] = []

    before = db.count_analyses()
    edges_found = 0
    try:
        edges_found = len(scanner.scan(_build_request()))
    except Exception as e:  # noqa: BLE001
        errors.append(f"scan: {type(e).__name__}: {e}")
    markets_scanned = max(0, db.count_analyses() - before)

    resolutions_captured = 0
    try:
        resolutions_captured = scanner.sweep_resolutions()
    except Exception as e:  # noqa: BLE001
        errors.append(f"sweep: {type(e).__name__}: {e}")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets_scanned": markets_scanned,
        "edges_found": edges_found,
        "resolutions_captured": resolutions_captured,
        "errors": errors,
    }
    try:
        path = _scan_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:  # noqa: BLE001 — logging failure must not kill the run
        _log.warning("scan_log write failed: %s", e)

    _log.info(
        "auto-scan: scanned=%d edges=%d resolutions=%d errors=%d",
        markets_scanned, edges_found, resolutions_captured, len(errors),
    )
    return record


def _interval_seconds() -> float:
    try:
        return float(os.getenv("SCAN_INTERVAL_HOURS") or 0) * 3600.0
    except ValueError:
        return 0.0


def _tick() -> None:
    try:
        run_once()
    finally:
        # Re-arm AFTER the run so cycles never overlap (period ~= interval + run time).
        _arm(_interval_seconds())


def _arm(interval_s: float) -> None:
    global _timer
    _timer = threading.Timer(interval_s, _tick)
    _timer.daemon = True
    _timer.start()


def start() -> None:
    """Arm the recurring scan if SCAN_INTERVAL_HOURS > 0. Call once, from __main__."""
    interval_s = _interval_seconds()
    if interval_s <= 0:
        _log.info("auto-scan scheduler disabled (set SCAN_INTERVAL_HOURS to enable)")
        return
    _arm(interval_s)
    _log.info("auto-scan scheduler armed (every %.2fh)", interval_s / 3600.0)
