"""Per-model LLM pricing — turn token counts into a rough USD cost.

Pure stdlib. ``RATES`` is USD per 1,000,000 tokens as ``(input, output)``, from public list
pricing — **approximate and editable**; update as prices change. An unknown model falls back to a
conservative default (logged once) so cost reporting degrades gracefully instead of failing.

Tokens are stored on each ``Analysis`` (durable, price-independent); dollar figures are always
derived here, so re-pricing history is just a table edit.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

# USD per 1M tokens: (input, output). Approximate public prices — edit to taste.
RATES: dict[str, tuple[float, float]] = {
    "gpt-5.5": (1.25, 10.00),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o": (2.50, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-1": (15.00, 75.00),
}
# Used when a model isn't in RATES (kept deliberately on the higher side so unknown models
# aren't under-counted). Web search adds provider fees this flat table doesn't model.
FALLBACK_RATE: tuple[float, float] = (3.00, 15.00)

_warned: set[str] = set()


def rate_for(model: str | None) -> tuple[float, float]:
    """(input, output) USD-per-1M for ``model``; the fallback (logged once) if unknown."""
    key = model or ""
    if key in RATES:
        return RATES[key]
    if key not in _warned:
        _log.warning("no pricing for model %r; using fallback rate %s/1M", model, FALLBACK_RATE)
        _warned.add(key)
    return FALLBACK_RATE


def cost_usd(model: str | None, input_tokens: int | None, output_tokens: int | None) -> float:
    """Rough USD cost of one call given its token usage. 0.0 when usage is missing/zero."""
    rate_in, rate_out = rate_for(model)
    it = input_tokens or 0
    ot = output_tokens or 0
    return (it * rate_in + ot * rate_out) / 1_000_000.0
