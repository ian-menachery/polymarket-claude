"""Headless-browser smoke test: the single-page app must actually mount.

Every other test is backend/JSON and never executes the frontend — which is how an unpinned
``@babel/standalone`` CDN drift blanked the whole UI while CI stayed green. ``test_frontend_pinned``
is the *static* guard (tags stay pinned); this is the *dynamic* one: serve the real app, load it in
headless Chrome, and assert React rendered. Skips cleanly when selenium or a browser is absent, so a
browserless CI still passes green (GitHub's Ubuntu runners ship Chrome, so it runs there).
"""

from __future__ import annotations

import socket
import threading

import pytest

pytest.importorskip("selenium")

from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.options import Options  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    """Serve the real Flask app on an ephemeral port against a throwaway DB (no scheduler)."""
    monkeypatch.setenv("RESEARCH_DB_PATH", str(tmp_path / "smoke.db"))
    from werkzeug.serving import make_server

    from research import app as appmod  # imported after RESEARCH_DB_PATH is set

    appmod.db.init_db()
    port = _free_port()
    server = make_server("127.0.0.1", port, appmod.app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def _make_driver():
    opts = Options()
    for arg in ("--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1280,1000"):
        opts.add_argument(arg)
    return webdriver.Chrome(options=opts)


def test_app_mounts(live_server) -> None:
    try:
        driver = _make_driver()
    except Exception as e:  # noqa: BLE001 — no browser/driver here; that's a skip, not a failure
        pytest.skip(f"no headless browser available: {e}")
    try:
        driver.get(live_server + "/")
        # React + in-browser Babel must transform and mount; a JS error (e.g. the CDN-drift bug)
        # leaves <div id="root"> empty and these waits time out -> the test fails, as intended.
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tab")))
        assert "PMRA" in driver.find_element(By.CSS_SELECTOR, "h1").text
        tabs = [t.text for t in driver.find_elements(By.CSS_SELECTOR, ".tab")]
        assert "Markets" in tabs, f"expected the Markets tab, got: {tabs}"
    finally:
        driver.quit()
