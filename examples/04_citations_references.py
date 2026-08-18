"""Citation graph: GET /paper/{id}/citations and /paper/{id}/references.

Edge fields (contexts, intents, isInfluential) describe the citation itself,
not the papers on either end.
"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

PAPER = "ARXIV:1706.03762"

with S2Client() as client:
    citations = client.citations(PAPER, fields="title,year,isInfluential,intents", limit=5)
    print("Recent papers citing it:")
    for edge in citations["data"]:
        paper = edge["citingPaper"]
        flag = " [influential]" if edge["isInfluential"] else ""
        print(f"  [{paper.get('year')}] {paper['title']}{flag} intents={edge['intents']}")

    references = client.references(PAPER, fields="title,year", limit=5)
    print("\nPapers it cites:")
    for edge in references["data"]:
        paper = edge["citedPaper"]
        print(f"  [{paper.get('year')}] {paper['title']}")
