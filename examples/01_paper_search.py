"""Relevance search: GET /graph/v1/paper/search"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    result = client.search_papers(
        "construction of the Panama Canal",
        fields="title,year,citationCount,externalIds",
        limit=5,
        filters={"year": "2010-", "minCitationCount": "10"},
    )

    print(f"{result['total']} total matches, showing {len(result['data'])}:\n")
    for paper in result["data"]:
        doi = (paper.get("externalIds") or {}).get("DOI", "-")
        print(f"  [{paper['year']}] {paper['title']}")
        print(f"         cites={paper['citationCount']}  doi={doi}")
