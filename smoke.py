"""Live smoke test — one cheap call per API surface. Run: uv run smoke.py

Unauthenticated requests share a global pool, so 429s (handled by backoff)
are normal; the run may just be slow.
"""

from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv

from s2 import S2Client

load_dotenv()


def main() -> int:
    client = S2Client()
    checks: list[tuple[str, Callable[[], Any]]] = [
        ("paper search", lambda: client.search_papers("attention transformers", limit=1)["data"]),
        ("paper details", lambda: client.paper("ARXIV:1706.03762", fields="title")["title"]),
        ("paper batch", lambda: client.papers(["ARXIV:1706.03762"], fields="title")[0]),
        ("citations", lambda: client.citations("ARXIV:1706.03762", limit=1)["data"]),
        ("author search", lambda: client.search_authors("Oren Etzioni", limit=1)["data"]),
        ("recommendations", lambda: client.recommendations("ARXIV:1706.03762", limit=1)),
        ("bulk search", lambda: next(client.iter_search_bulk("semantic scholar api"))),
        ("datasets", lambda: client.dataset_releases()[-1]),
    ]

    print(f"key: {'set' if client.api_key else 'none (shared unauthenticated pool)'}\n")
    failures = 0
    for name, check in checks:
        try:
            check()
            print(f"  PASS  {name}")
        except Exception as error:  # noqa: BLE001 - report every failure, keep going
            failures += 1
            print(f"  FAIL  {name}: {error}")

    client.close()
    print(f"\n{len(checks) - failures}/{len(checks)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
