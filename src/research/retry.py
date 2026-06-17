"""Generic synchronous retry helper for transient failures.

stdlib only (``time`` + ``random``) and deliberately free of any HTTP/SDK imports, so it
doesn't breach the module boundary (HTTP types live in ``polymarket``/``kalshi``). Callers
supply the exception types to retry and an optional ``giveup`` predicate to bail early on a
non-retryable error (e.g. an HTTP 4xx). Backoff is capped exponential with jitter, so a flaky
endpoint never causes a runaway wait or a synchronized thundering-herd retry.
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def call_with_retries(
    fn: Callable[[], T],
    *,
    retry_on: tuple[type[BaseException], ...],
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    giveup: Callable[[BaseException], bool] | None = None,
) -> T:
    """Call ``fn``, retrying ``retry_on`` exceptions with capped exponential backoff + jitter.

    Re-raises immediately when ``giveup(exc)`` is True (a non-retryable error) or on the final
    attempt; any exception not in ``retry_on`` propagates unchanged.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on as e:
            if attempt == attempts - 1 or (giveup is not None and giveup(e)):
                raise
            delay = min(max_delay, base_delay * (2 ** attempt))
            time.sleep(delay + random.uniform(0.0, delay * 0.1))
    raise AssertionError("unreachable")  # pragma: no cover
