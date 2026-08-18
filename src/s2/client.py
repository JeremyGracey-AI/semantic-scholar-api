"""Minimal Semantic Scholar API client.

Covers the Academic Graph, Recommendations, and Datasets APIs.
Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any, Literal

import httpx

GRAPH = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS = "https://api.semanticscholar.org/recommendations/v1"
DATASETS = "https://api.semanticscholar.org/datasets/v1"

DEFAULT_FIELDS = "title,year,authors"
_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5


class S2ApiError(Exception):
    """Non-retryable API error (or retries exhausted)."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def _backoff(attempt: int) -> float:
    return min(2.0**attempt, 30.0)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after", "")
    if retry_after.isdigit():
        return float(retry_after)
    return _backoff(attempt)


class S2Client:
    """Sync client for the Semantic Scholar APIs.

    Reads the API key from the S2_API_KEY env var unless passed explicitly;
    works without one (shared unauthenticated rate-limit pool). Retries
    429/5xx (honoring Retry-After) and transport errors (timeouts,
    connection failures) with exponential backoff, and spaces requests
    `min_interval` seconds apart (authenticated tier allows
    1 request/second).

    Paper IDs accept the S2 sha or a prefixed external ID:
    DOI:10.18653/v1/N18-3011, ARXIV:2106.15928, PMID:19872477,
    CorpusId:215416146, ACL:W12-3903, URL:https://arxiv.org/abs/...
    """

    def __init__(
        self,
        api_key: str | None = None,
        min_interval: float = 1.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = api_key or os.environ.get("S2_API_KEY") or None
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        self._http = httpx.Client(headers=headers, timeout=30.0, transport=transport)
        self._min_interval = min_interval
        self._last_request_at = 0.0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> S2Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- core --------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        for attempt in range(_MAX_RETRIES):
            self._throttle()
            try:
                response = self._http.request(method, url, params=params, json=json)
            except httpx.TransportError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(_backoff(attempt))
                continue
            if response.is_success:
                return response.json()
            if response.status_code in _RETRYABLE and attempt < _MAX_RETRIES - 1:
                time.sleep(_retry_delay(response, attempt))
                continue
            raise S2ApiError(response.status_code, response.text)
        raise AssertionError("unreachable")

    def _throttle(self) -> None:
        wait = self._min_interval - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    # -- papers ------------------------------------------------------------

    def paper(self, paper_id: str, fields: str = DEFAULT_FIELDS) -> dict[str, Any]:
        return self._request("GET", f"{GRAPH}/paper/{paper_id}", params={"fields": fields})

    def papers(self, ids: list[str], fields: str = DEFAULT_FIELDS) -> list[dict[str, Any] | None]:
        """Batch lookup, up to 500 IDs. Unknown IDs come back as None."""
        if not 0 < len(ids) <= 500:
            raise ValueError(f"batch accepts 1-500 ids, got {len(ids)}")
        return self._request(
            "POST", f"{GRAPH}/paper/batch", params={"fields": fields}, json={"ids": ids}
        )

    def search_papers(
        self,
        query: str,
        fields: str = DEFAULT_FIELDS,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Relevance-ranked search. Returns {total, offset, next?, data}.

        `filters` maps to documented query params: year, venue, fieldsOfStudy,
        publicationTypes, openAccessPdf, minCitationCount, publicationDateOrYear.
        """
        params = {"query": query, "fields": fields, "limit": limit, "offset": offset}
        return self._request("GET", f"{GRAPH}/paper/search", params=params | (filters or {}))

    def match_paper(self, title: str, fields: str = DEFAULT_FIELDS) -> dict[str, Any]:
        """Closest single match for a title; includes matchScore."""
        data = self._request(
            "GET", f"{GRAPH}/paper/search/match", params={"query": title, "fields": fields}
        )
        return data["data"][0]

    def iter_search_bulk(
        self,
        query: str,
        fields: str = DEFAULT_FIELDS,
        sort: str | None = None,
        filters: dict[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yields every match, 1000 per page via token pagination. Not relevance-ranked.

        Supports boolean query syntax: 'fish ladder' -"bass" +migration, etc.
        `sort`: e.g. 'citationCount:desc', 'publicationDate:asc'.
        """
        params: dict[str, Any] = {"query": query, "fields": fields} | (filters or {})
        if sort:
            params["sort"] = sort
        while True:
            page = self._request("GET", f"{GRAPH}/paper/search/bulk", params=params)
            yield from page["data"]
            if not page.get("token"):
                return
            params["token"] = page["token"]

    def citations(
        self,
        paper_id: str,
        fields: str = DEFAULT_FIELDS,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Papers citing `paper_id`. Edge fields: contexts, intents, isInfluential."""
        return self._request(
            "GET",
            f"{GRAPH}/paper/{paper_id}/citations",
            params={"fields": fields, "limit": limit, "offset": offset},
        )

    def references(
        self,
        paper_id: str,
        fields: str = DEFAULT_FIELDS,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Papers cited by `paper_id`. Same edge fields as citations()."""
        return self._request(
            "GET",
            f"{GRAPH}/paper/{paper_id}/references",
            params={"fields": fields, "limit": limit, "offset": offset},
        )

    # -- authors -----------------------------------------------------------

    def author(self, author_id: str, fields: str = "name,affiliations,hIndex") -> dict[str, Any]:
        return self._request("GET", f"{GRAPH}/author/{author_id}", params={"fields": fields})

    def authors(
        self, ids: list[str], fields: str = "name,affiliations,hIndex"
    ) -> list[dict[str, Any] | None]:
        """Batch lookup, up to 1000 IDs."""
        if not 0 < len(ids) <= 1000:
            raise ValueError(f"batch accepts 1-1000 ids, got {len(ids)}")
        return self._request(
            "POST", f"{GRAPH}/author/batch", params={"fields": fields}, json={"ids": ids}
        )

    def search_authors(
        self, query: str, fields: str = "name,affiliations,hIndex", limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{GRAPH}/author/search",
            params={"query": query, "fields": fields, "limit": limit, "offset": offset},
        )

    def author_papers(
        self, author_id: str, fields: str = DEFAULT_FIELDS, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{GRAPH}/author/{author_id}/papers",
            params={"fields": fields, "limit": limit, "offset": offset},
        )

    # -- recommendations ---------------------------------------------------

    def recommendations(
        self,
        paper_id: str,
        fields: str = DEFAULT_FIELDS,
        limit: int = 10,
        pool: Literal["recent", "all-cs"] = "recent",
    ) -> list[dict[str, Any]]:
        """Papers similar to `paper_id`, drawn from the given pool."""
        data = self._request(
            "GET",
            f"{RECOMMENDATIONS}/papers/forpaper/{paper_id}",
            params={"fields": fields, "limit": limit, "from": pool},
        )
        return data["recommendedPapers"]

    def recommendations_from_lists(
        self,
        positive_ids: list[str],
        negative_ids: list[str] | None = None,
        fields: str = DEFAULT_FIELDS,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recommendations from example papers you like (and optionally dislike)."""
        data = self._request(
            "POST",
            f"{RECOMMENDATIONS}/papers",
            params={"fields": fields, "limit": limit},
            json={"positivePaperIds": positive_ids, "negativePaperIds": negative_ids or []},
        )
        return data["recommendedPapers"]

    # -- datasets ----------------------------------------------------------

    def dataset_releases(self) -> list[str]:
        """All release IDs (dated snapshots of the full corpus)."""
        return self._request("GET", f"{DATASETS}/release")

    def dataset_release(self, release_id: str = "latest") -> dict[str, Any]:
        """Datasets available in one release. Downloading files requires an API key."""
        return self._request("GET", f"{DATASETS}/release/{release_id}")
