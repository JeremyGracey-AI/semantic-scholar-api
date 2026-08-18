# semantic-scholar-api

Thin client + runnable examples for the [Semantic Scholar API](https://www.semanticscholar.org/product/api)
(Academic Graph, Recommendations, Datasets).

## Quickstart

```bash
uv sync
cp .env.example .env        # add S2_API_KEY when you have one — works without
uv run smoke.py             # live check, one call per API surface
uv run examples/01_paper_search.py
uv run marimo edit notebooks/explore.py   # interactive explorer
```

## Layout

| Path | What |
|---|---|
| `src/s2/client.py` | `S2Client` — key-optional, 429/5xx + network-error backoff (honors `Retry-After`), 1 req/s throttle |
| `examples/01_paper_search.py` | Relevance search with filters (`year`, `minCitationCount`, …) |
| `examples/02_paper_details.py` | Single paper by any ID form + fuzzy title match |
| `examples/03_paper_batch.py` | POST batch — up to 500 papers in one request |
| `examples/04_citations_references.py` | Citation graph edges (`isInfluential`, `intents`, `contexts`) |
| `examples/05_authors.py` | Author search, details, papers |
| `examples/06_recommendations.py` | Similar papers from a seed, or positive/negative lists |
| `examples/07_bulk_search.py` | Full result sets, 1000/page token pagination, boolean queries |
| `examples/08_datasets.py` | Corpus snapshot releases (downloads need a key) |
| `notebooks/explore.py` | marimo explorer — search UI → paper details, citation-flow diagram, recommendations |
| `smoke.py` | Live end-to-end check |
| `tests/` | Mocked-transport unit tests, no network |

## API notes

- Base URLs: `…/graph/v1`, `…/recommendations/v1`, `…/datasets/v1` on `api.semanticscholar.org`.
- Auth: `x-api-key` header, read from `S2_API_KEY`. No key → shared unauthenticated pool
  (429s are normal; the client backs off and retries). Key → 1 request/second.
  [Request a key](https://www.semanticscholar.org/product/api#api-key).
- Paper IDs: S2 sha or prefixed — `DOI:…`, `ARXIV:…`, `PMID:…`, `CorpusId:…`, `ACL:…`, `URL:…`.
- Always pass `fields=` — default responses are minimal.
- Relevance search caps at 100/page (1,000 total); bulk search returns everything at 1000/page.
- Prefer batch endpoints over loops: one request instead of N.
- Not wrapped here: `GET /paper/{id}/authors`, snippet search, dataset diffs — add to
  `client.py` if needed. [Full docs](https://api.semanticscholar.org/api-docs/).

## Validation

```bash
uv run ruff check .
uv run pyright
uv run pytest
```
