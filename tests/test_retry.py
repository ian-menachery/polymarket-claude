"""Tests for the generic retry helper (research.retry.call_with_retries)."""

from __future__ import annotations

import pytest

from research.retry import call_with_retries


class Boom(Exception):
    pass


class Other(Exception):
    pass


def test_succeeds_after_retries() -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise Boom()
        return "ok"

    out = call_with_retries(fn, retry_on=(Boom,), attempts=3, base_delay=0)
    assert out == "ok"
    assert calls["n"] == 3


def test_exhausts_attempts_then_raises() -> None:
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise Boom()

    with pytest.raises(Boom):
        call_with_retries(fn, retry_on=(Boom,), attempts=3, base_delay=0)
    assert calls["n"] == 3  # tried exactly `attempts` times


def test_giveup_skips_retry() -> None:
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise Boom()

    with pytest.raises(Boom):
        call_with_retries(fn, retry_on=(Boom,), attempts=5, base_delay=0, giveup=lambda e: True)
    assert calls["n"] == 1  # gave up immediately, no retries


def test_non_retryable_exception_propagates_immediately() -> None:
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise Other()

    with pytest.raises(Other):
        call_with_retries(fn, retry_on=(Boom,), attempts=3, base_delay=0)
    assert calls["n"] == 1
