"""Bulk search: GET /paper/search/bulk — every match, 1000/page, token pagination.

Use this (not relevance search) when you want the full result set.
Supports boolean syntax in the query and sort=field:direction.
"""

import itertools

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    papers = client.iter_search_bulk(
        '"semantic scholar" +api',
        fields="title,year,citationCount",
        sort="citationCount:desc",
        filters={"year": "2020-"},
    )
    # The iterator pages through everything; take just the first 10 here.
    for paper in itertools.islice(papers, 10):
        print(f"  [{paper.get('year')}] cites={paper['citationCount']:>5}  {paper['title']}")
