"""Recommendations API: papers similar to a seed paper, or to liked/disliked lists."""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    print("Similar to 'Attention Is All You Need':")
    for paper in client.recommendations("ARXIV:1706.03762", fields="title,year", limit=5):
        print(f"  [{paper.get('year')}] {paper['title']}")

    print("\nFrom positive/negative examples:")
    recs = client.recommendations_from_lists(
        positive_ids=["ARXIV:1706.03762", "ARXIV:1810.04805"],  # transformers, BERT
        negative_ids=["ARXIV:1512.03385"],                      # ResNet
        fields="title,year",
        limit=5,
    )
    for paper in recs:
        print(f"  [{paper.get('year')}] {paper['title']}")
