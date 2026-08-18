"""Single paper lookup: GET /graph/v1/paper/{id} — plus title match.

Any ID form works: S2 sha, DOI:..., ARXIV:..., PMID:..., CorpusId:..., URL:...
"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    paper = client.paper(
        "ARXIV:1706.03762",  # "Attention Is All You Need"
        fields="title,year,abstract,citationCount,tldr,fieldsOfStudy",
    )
    print(paper["title"], f"({paper['year']})")
    print(f"citations: {paper['citationCount']}")
    if paper.get("tldr"):
        print(f"tldr: {paper['tldr']['text']}")

    # Fuzzy title match when you don't have an ID:
    match = client.match_paper("attention is all you need", fields="title,year")
    print(f"\nmatch: {match['title']} ({match['year']}) score={match['matchScore']:.1f}")
