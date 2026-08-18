"""Authors: GET /author/search, /author/{id}, /author/{id}/papers"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    hits = client.search_authors("Oren Etzioni", fields="name,hIndex,paperCount", limit=3)
    for author in hits["data"]:
        print(f"  {author['name']}  authorId={author['authorId']}  "
              f"h={author['hIndex']}  papers={author['paperCount']}")

    top = hits["data"][0]
    papers = client.author_papers(top["authorId"], fields="title,year,citationCount", limit=5)
    print(f"\nRecent papers by {top['name']}:")
    for paper in papers["data"]:
        print(f"  [{paper.get('year')}] {paper['title']} (cites={paper['citationCount']})")
