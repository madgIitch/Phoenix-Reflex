from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a Phoenix Reflex prompt tag.")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--source-tag", default="candidate")
    parser.add_argument("--target-tag", default="staging")
    args = parser.parse_args()

    url = (
        f"{args.base_url.rstrip('/')}/prompts/promote"
        f"?source_tag={args.source_tag}&target_tag={args.target_tag}"
    )
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
