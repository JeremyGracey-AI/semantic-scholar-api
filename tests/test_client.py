"""Unit tests against a mocked transport — no network."""

import json

import httpx
import pytest

from s2 import S2ApiError, S2Client


def make_client(handler, api_key: str | None = None) -> S2Client:
    return S2Client(
        api_key=api_key, min_interval=0.0, transport=httpx.MockTransport(handler)
    )


@pytest.fixture(autouse=True)
def no_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S2_API_KEY", raising=False)


def test_search_builds_params() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"total": 0, "data": []})

    with make_client(handler) as client:
        client.search_papers("canal", fields="title", limit=3, filters={"year": "2020-"})

    expected = {"query": "canal", "fields": "title", "limit": "3", "offset": "0", "year": "2020-"}
    assert seen == expected


def test_api_key_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "sekret"
        return httpx.Response(200, json={})

    with make_client(handler, api_key="sekret") as client:
        client.paper("ARXIV:1706.03762")


def test_no_key_sends_no_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "x-api-key" not in request.headers
        return httpx.Response(200, json={})

    with make_client(handler) as client:
        client.paper("ARXIV:1706.03762")


def test_retries_429_then_succeeds() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"title": "ok"})

    with make_client(handler) as client:
        assert client.paper("x")["title"] == "ok"
    assert len(calls) == 3


def test_retries_transport_error_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("s2.client.time.sleep", sleeps.append)
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ConnectError("connection reset", request=request)
        return httpx.Response(200, json={"title": "ok"})

    with make_client(handler) as client:
        assert client.paper("x")["title"] == "ok"
    assert len(calls) == 3
    assert len(sleeps) == 2  # backed off between attempts


def test_transport_error_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("s2.client.time.sleep", lambda _delay: None)
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    with make_client(handler) as client, pytest.raises(httpx.ReadTimeout):
        client.paper("x")
    assert len(calls) == 5


def test_gives_up_after_max_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "0"})

    with make_client(handler) as client, pytest.raises(S2ApiError) as excinfo:
        client.paper("x")
    assert excinfo.value.status_code == 429


def test_client_error_raises_without_retry() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400, text="bad query")

    with make_client(handler) as client, pytest.raises(S2ApiError) as excinfo:
        client.search_papers("")
    assert excinfo.value.status_code == 400
    assert len(calls) == 1


def test_batch_posts_ids() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/graph/v1/paper/batch"
        assert json.loads(request.content) == {"ids": ["a", "b"]}
        return httpx.Response(200, json=[{"title": "A"}, None])

    with make_client(handler) as client:
        assert client.papers(["a", "b"]) == [{"title": "A"}, None]


def test_batch_rejects_bad_sizes() -> None:
    client = make_client(lambda request: httpx.Response(200))
    with pytest.raises(ValueError, match="1-500"):
        client.papers(["x"] * 501)
    with pytest.raises(ValueError, match="1-500"):
        client.papers([])
    client.close()


def test_author_batch_rejects_oversize() -> None:
    client = make_client(lambda request: httpx.Response(200))
    with pytest.raises(ValueError, match="1-1000"):
        client.authors(["x"] * 1001)
    client.close()


def test_bulk_search_follows_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("token") == "t1":
            return httpx.Response(200, json={"data": [{"title": "p2"}]})
        return httpx.Response(200, json={"data": [{"title": "p1"}], "token": "t1"})

    with make_client(handler) as client:
        titles = [paper["title"] for paper in client.iter_search_bulk("q")]
    assert titles == ["p1", "p2"]


def test_recommendations_unwraps_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["from"] == "recent"
        return httpx.Response(200, json={"recommendedPapers": [{"title": "r"}]})

    with make_client(handler) as client:
        assert client.recommendations("x") == [{"title": "r"}]
