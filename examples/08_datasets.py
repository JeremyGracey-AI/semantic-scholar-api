"""Datasets API: dated full-corpus snapshots for offline/bulk work.

Listing releases works without a key; downloading dataset files requires one.
"""

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()

with S2Client() as client:
    releases = client.dataset_releases()
    print(f"{len(releases)} releases; latest 3: {releases[-3:]}")

    latest = client.dataset_release("latest")
    print(f"\nDatasets in release {latest['release_id']}:")
    for dataset in latest["datasets"]:
        print(f"  {dataset['name']:20s} {dataset['description'][:70]}")
