"""Move a board card and/or add an evidence comment (WP-37). Agents use this.

  PLANE_API_TOKEN=... python3 card.py WP-41 --state "Needs review" --comment "evidence…"

The card is found by its title prefix ("WP-41 …"). Only Mario, or Claude after
Mario's live review, moves a card to Done. Stdlib only.
"""

import argparse
import html
import json
import os
import urllib.request

BASE = os.environ.get("PLANE_URL", "https://plane.clockmost.com").rstrip("/")
WS = os.environ.get("PLANE_WORKSPACE", "clockmost")
PROJECT = os.environ.get("PLANE_PROJECT", "FELT")


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{BASE}/api/v1/workspaces/{WS}/{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "X-API-Key": os.environ["PLANE_API_TOKEN"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="title prefix, e.g. WP-41")
    ap.add_argument("--state", help="column name, e.g. 'Needs review'")
    ap.add_argument(
        "--comment", help="plain-text comment (paragraphs split on blank lines)"
    )
    args = ap.parse_args()

    project = next(
        p for p in call("GET", "projects/")["results"] if p["identifier"] == PROJECT
    )
    pid = project["id"]
    issues = call("GET", f"projects/{pid}/issues/?per_page=100")["results"]
    matches = [i for i in issues if i["name"].startswith(args.key + " ")]
    if len(matches) != 1:
        raise SystemExit(f"{args.key}: {len(matches)} cards match")
    card = matches[0]
    if args.state:
        states = {
            s["name"]: s["id"]
            for s in call("GET", f"projects/{pid}/states/")["results"]
        }
        call(
            "PATCH",
            f"projects/{pid}/issues/{card['id']}/",
            {"state": states[args.state]},
        )
        print(f"{args.key} -> {args.state}")
    if args.comment:
        paras = "".join(
            f"<p>{html.escape(p.strip())}</p>"
            for p in args.comment.split("\n\n")
            if p.strip()
        )
        call(
            "POST",
            f"projects/{pid}/issues/{card['id']}/comments/",
            {"comment_html": paras},
        )
        print(f"{args.key}: comment added")


if __name__ == "__main__":
    main()
