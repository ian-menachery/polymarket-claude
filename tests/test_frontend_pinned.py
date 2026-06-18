"""Guard against the blank-UI regression: frontend CDN scripts must be version-pinned.

The whole web app once rendered blank because ``frontend/index.html`` loaded
``@babel/standalone`` (and React) from unpkg with no pinned version — a newer "latest"
build changed the React preset's default JSX runtime and broke the in-browser transform.
No other test executes the frontend (all are backend/JSON), so this is the cheap, browser-free
check that the script tags stay pinned to at least ``@<major>.<minor>``.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/ sits at the repo root, so parents[1] is the project root (mirrors how
# app._FRONTEND_DIR resolves frontend/ from src/research/app.py via parents[2]).
_INDEX_HTML = Path(__file__).resolve().parents[1] / "frontend" / "index.html"

# Captures the spec after "unpkg.com/" up to the closing quote, e.g.
# "react@18.3.1/umd/react.development.js" or "@babel/standalone@7.26.4/babel.min.js".
_UNPKG = re.compile(r"unpkg\.com/([^\"']+)")
# An explicit version pin: "@<major>.<minor>" somewhere in the spec. A scoped package's
# leading "@babel" has no digits, so this only matches the real version (e.g. "@7.26").
_PINNED = re.compile(r"@\d+\.\d+")


def test_cdn_scripts_are_version_pinned() -> None:
    html = _INDEX_HTML.read_text(encoding="utf-8")
    specs = _UNPKG.findall(html)

    # Non-empty so a future HTML/regex change can't make this pass vacuously — the app
    # loads react, react-dom, and @babel/standalone from unpkg.
    assert len(specs) >= 3, f"expected the React/Babel unpkg scripts, found: {specs}"

    unpinned = [s for s in specs if not _PINNED.search(s)]
    assert not unpinned, (
        "unpinned unpkg script(s) in frontend/index.html — pin to @<major>.<minor> to keep the "
        f"build deterministic (an unpinned @babel/standalone once blanked the UI): {unpinned}"
    )
