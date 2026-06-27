"""Message Batches: db state round-trip + analyzer batch helpers/parsing (mocked, no network)."""

from __future__ import annotations

from conftest import make_market

from research import analyzer


# --- db batch-state round-trip -------------------------------------------------


def test_batch_state_roundtrip(temp_db) -> None:
    db = temp_db
    assert db.get_inflight_batch() is None
    db.save_batch("batch_abc", request_count=7)
    inflight = db.get_inflight_batch()
    assert inflight is not None
    assert inflight["id"] == "batch_abc"
    assert inflight["status"] == "submitted"
    assert inflight["request_count"] == 7

    db.mark_batch_ingested("batch_abc")
    assert db.get_inflight_batch() is None  # no longer 'submitted'


# --- analyzer batch helpers (mocked client) ------------------------------------


class _Usage:
    def __init__(self, i: int, o: int, cc: int = 0, cr: int = 0) -> None:
        self.input_tokens = i
        self.output_tokens = o
        self.cache_creation_input_tokens = cc
        self.cache_read_input_tokens = cr


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Msg:
    """A batch result's `.result.message` — same content-block shape as a live response."""

    def __init__(self, text: str, i: int, o: int) -> None:
        self.content = [_TextBlock(text)]
        self.usage = _Usage(i, o)


class _FakeBatches:
    def __init__(self) -> None:
        self.submitted: list = []

    def create(self, requests):  # noqa: ANN001
        self.submitted = list(requests)
        return type("B", (), {"id": "batch_xyz"})()

    def retrieve(self, _id):  # noqa: ANN001
        return type("B", (), {"processing_status": "ended"})()

    def results(self, _id):  # noqa: ANN001
        return iter([])


class _FakeClient:
    def __init__(self) -> None:
        self.messages = type("M", (), {"batches": _FakeBatches()})()


_JSON = '{"probability": 55, "confidence": "medium", "summary": "s", "factors": ["a"]}'


def test_batch_request_params_match_sync_shape() -> None:
    params = analyzer.batch_request_params(make_market(market_prob=0.5))
    assert params["model"]  # ANALYSIS_MODEL or default
    assert params["tools"] == [analyzer.WEB_SEARCH_TOOL]
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert params["messages"][0]["role"] == "user"


def test_submit_and_status(monkeypatch) -> None:
    client = _FakeClient()
    monkeypatch.setattr(analyzer, "_get_client", lambda: client)
    bid = analyzer.submit_batch([{"custom_id": "m1", "params": {"x": 1}}])
    assert bid == "batch_xyz"
    assert client.messages.batches.submitted == [{"custom_id": "m1", "params": {"x": 1}}]
    assert analyzer.batch_status(bid) == "ended"


def test_parse_batch_result_stamps_tokens() -> None:
    a = analyzer.parse_batch_result(_Msg(_JSON, 800, 200), make_market(market_prob=0.4), "claude-sonnet-4-6")
    assert a.error is None
    assert a.claude_prob == 0.55  # parsed from the message's final text block
    assert (a.input_tokens, a.output_tokens) == (800, 200)
    assert a.model == "claude-sonnet-4-6"
