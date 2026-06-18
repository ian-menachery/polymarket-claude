"""Exchange dispatch — the one place that knows which client handles which exchange.

Routes the per-exchange operations (fetch active markets, order book, resolution) to the right
client, by the ``EXCHANGE`` env var or a market's own ``.exchange`` tag. This is the single seam to
touch when adding an exchange; callers (``scanner``, ``app``) stay exchange-agnostic. It imports the
clients but performs no HTTP itself — the httpx boundary stays in ``polymarket.py`` / ``kalshi.py``.

Consolidating this here also fixes a latent bug: the manual refresh and the resolution sweep used
to call Polymarket directly, ignoring ``EXCHANGE`` / a market's exchange (so Kalshi markets were
never refreshed or resolution-checked).
"""

from __future__ import annotations

import logging
import os

from research import kalshi, polymarket
from research.models import Market

_log = logging.getLogger(__name__)


def fetch_active(max_markets: int) -> list[Market]:
    """Active markets from the exchange(s) ``EXCHANGE`` selects.

    ``polymarket`` (default) | ``kalshi`` | ``both``. For ``both`` we pull up to ``max_markets``
    from each and concatenate — the combined list can exceed ``max_markets``, but downstream
    pre-filters bound how many are actually analyzed.
    """
    exchange = os.getenv("EXCHANGE", "polymarket").strip().lower()
    if exchange == "kalshi":
        return kalshi.fetch_all_active(max_markets=max_markets)
    if exchange == "both":
        return (
            polymarket.fetch_all_active(max_markets=max_markets)
            + kalshi.fetch_all_active(max_markets=max_markets)
        )
    return polymarket.fetch_all_active(max_markets=max_markets)


def fetch_book(market: Market) -> polymarket.Book | None:
    """Order book for a market, exchange-aware; ``None`` if unavailable (caller uses the mid).

    Polymarket books key off the CLOB ``yes_token_id``; Kalshi books key off the ticker
    (``market.id``) and come back already in the same YES-centric ``Book`` shape. A book hiccup
    must not kill the scan, so failures are logged at debug and degrade to ``None``.
    """
    try:
        if market.exchange == "kalshi":
            return kalshi.fetch_book(market.id)  # market.id is the Kalshi ticker
        if market.yes_token_id:
            return polymarket.fetch_book(market.yes_token_id)
    except Exception as e:  # noqa: BLE001 — a book hiccup shouldn't kill the scan
        _log.debug("order-book fetch failed for %s (%s): %s", market.id, market.exchange, e)
    return None


def fetch_resolution(market: Market) -> bool | None:
    """Resolved YES/NO outcome for a market, exchange-aware; ``None`` if not yet resolved."""
    if market.exchange == "kalshi":
        return kalshi.fetch_resolution(market.id)
    return polymarket.fetch_resolution(market.id)
