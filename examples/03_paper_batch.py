"""Batch lookup: POST /graph/v1/paper/batch — up to 500 IDs in one request.

Prefer this over N single lookups; it counts as one request against rate limits.
"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

IDS = [
    "ARXIV:1706.03762",       # Attention Is All You Need
    "DOI:10.18653/v1/N18-3011",
    "CorpusId:215416146",
    "ARXIV:0000.00000",       # bogus on purpose -> comes back as None
]

with S2Client() as client:
    for requested, paper in zip(IDS, client.papers(IDS, fields="title,year"), strict=True):
        found = f"{paper['title']} ({paper['year']})" if paper else "NOT FOUND"
        print(f"  {requested:28s} -> {found}")
