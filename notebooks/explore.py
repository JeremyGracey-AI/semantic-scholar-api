"""Semantic Scholar explorer — marimo notebook.

Run: uv run marimo edit notebooks/explore.py
"""

import marimo

app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        """
        # Semantic Scholar explorer

        Search → pick a paper in the table → details, citation graph, and
        recommendations update below. Works without a key (shared pool, so
        expect retry pauses); set `S2_API_KEY` in `.env` for a steady 1 req/s.
        """
    )
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    from dotenv import load_dotenv

    from s2 import S2ApiError, S2Client

    load_dotenv()
    client = S2Client()
    key_note = "key set · 1 req/s" if client.api_key else "no key · shared unauthenticated pool"
    mo.md(f"**Client ready** — {key_note}")
    return S2ApiError, client


@app.cell
def _(mo):
    query = mo.ui.text(value="AI agent governance", label="Query")
    year = mo.ui.text(value="2023-", label="Year (2023-, 2020-2024, …)")
    min_citations = mo.ui.number(start=0, stop=1_000_000, value=0, label="Min citations")
    limit = mo.ui.slider(start=5, stop=100, step=5, value=20, label="Results")
    go = mo.ui.run_button(label="Search")
    mo.vstack([query, mo.hstack([year, min_citations, limit], justify="start"), go])
    return go, limit, min_citations, query, year


@app.cell
def _(S2ApiError, client, go, limit, min_citations, mo, query, year):
    mo.stop(not go.value, mo.md("*Set your query and hit Search.*"))

    filters: dict[str, str] = {}
    if year.value.strip():
        filters["year"] = year.value.strip()
    if min_citations.value:
        filters["minCitationCount"] = str(int(min_citations.value))

    problem = ""
    try:
        found = client.search_papers(
            query.value,
            fields="title,year,citationCount,venue",
            limit=int(limit.value),
            filters=filters,
        )
    except S2ApiError as error:
        found = None
        problem = str(error)
    mo.stop(found is None, mo.md(f"**API error:** {problem}"))
    assert found is not None

    results = mo.ui.table(
        [
            {
                "title": paper["title"],
                "year": paper.get("year"),
                "citations": paper.get("citationCount"),
                "venue": paper.get("venue") or "",
                "paperId": paper["paperId"],
            }
            for paper in found["data"]
        ],
        selection="single",
        label=f"{found['total']:,} matches — select one",
    )
    results
    return (results,)


@app.cell
def _(mo, results):
    mo.stop(not results.value, mo.md("*Select a row above to load the paper.*"))
    picked = results.value[0]["paperId"]
    return (picked,)


@app.cell
def _(client, mo, picked):
    detail = client.paper(
        picked, fields="title,year,abstract,tldr,citationCount,url,externalIds"
    )
    title = detail["title"]
    heading = f"[{title}]({detail['url']})" if detail.get("url") else title
    tldr = (detail.get("tldr") or {}).get("text") or "—"
    abstract = detail.get("abstract") or "*no abstract available*"
    mo.md(
        f"## {heading}\n"
        f"**{detail.get('year')}** · {detail['citationCount']:,} citations\n\n"
        f"**tl;dr** {tldr}\n\n{abstract}"
    )
    return (detail,)


@app.cell
def _(client, picked):
    citing = client.citations(picked, fields="title,year,isInfluential", limit=10)["data"]
    cited = client.references(picked, fields="title,year", limit=10)["data"]
    return cited, citing


@app.cell
def _(cited, citing, detail, mo):
    def label(title: str | None) -> str:
        clean = (title or "untitled").replace('"', "'").replace("[", "(").replace("]", ")")
        return clean[:45] + "…" if len(clean) > 45 else clean

    lines = ["graph TD"]
    for index, edge in enumerate(citing[:5]):
        lines.append(f'    c{index}["{label(edge["citingPaper"].get("title"))}"] --> P')
    lines.append(f'    P(["{label(detail["title"])}"])')
    for index, edge in enumerate(cited[:5]):
        lines.append(f'    P --> r{index}["{label(edge["citedPaper"].get("title"))}"]')
    lines.append("    style P fill:#e8f0fe,stroke:#1a56db")

    mo.vstack(
        [
            mo.md("### Citation flow — citing papers → selected → its references"),
            mo.mermaid("\n".join(lines)),
        ]
    )
    return


@app.cell
def _(cited, citing, mo):
    def bullet(paper: dict, influential: bool = False) -> str:
        flag = " **[influential]**" if influential else ""
        return f"- [{paper.get('year')}] {paper.get('title')}{flag}"

    citing_md = "\n".join(
        bullet(edge["citingPaper"], edge.get("isInfluential", False)) for edge in citing
    )
    cited_md = "\n".join(bullet(edge["citedPaper"]) for edge in cited)
    mo.md(
        f"### Top citing papers\n{citing_md or '*none*'}\n\n"
        f"### References\n{cited_md or '*none*'}"
    )
    return


@app.cell
def _(client, mo, picked):
    recs = client.recommendations(picked, fields="title,year,citationCount", limit=8)
    recs_md = "\n".join(
        f"- [{paper.get('year')}] {paper['title']} ({paper.get('citationCount', 0):,} cites)"
        for paper in recs
    )
    mo.md(f"### Similar papers (Recommendations API)\n{recs_md or '*none*'}")
    return


if __name__ == "__main__":
    app.run()
