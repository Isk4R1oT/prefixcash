#!/usr/bin/env python3
"""Publish an article to dev.to via the public API.

Account: create one at dev.to → Settings → Account → API Keys → generate a key.
Then:

    export DEV_TO_API_KEY=...
    uv run python scripts/publish_article.py --file article.md [--published]

Default: creates a draft (published=false) so you can preview before going live.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

DEFAULT_TITLE = "Your LLM prompt cache is leaking money — I built a tool that finds the leak"
TAGS = ["llm", "prompt-caching", "finops"]
CANONICAL = "https://github.com/Isk4R1oT/prefixcash"


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish markdown article to dev.to via API")
    parser.add_argument("--file", required=True, help="path to the article markdown")
    parser.add_argument("--published", action="store_true", help="publish immediately (default: draft)")
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    api_key = os.environ.get("DEV_TO_API_KEY")
    if not api_key:
        sys.exit("DEV_TO_API_KEY is not set (dev.to → Settings → Account → API Keys)")

    with open(args.file, encoding="utf-8") as fh:
        body_markdown = fh.read()

    payload = json.dumps(
        {
            "article": {
                "title": args.title,
                "published": args.published,
                "body_markdown": body_markdown,
                "tags": TAGS,
                "description": args.description,
                "canonical_url": CANONICAL,
            }
        }
    ).encode()

    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    state = "published" if args.published else "draft"
    print(f"{state}: {data.get('url') or data.get('slug')}")


if __name__ == "__main__":
    main()
