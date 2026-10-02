"""WP-37: board metrics from Plane's card-move history (read-only).

Per ticket that has moved since the board went live (2026-10-02):
  - cycle time: first move into "In progress" -> last move into "Done";
  - review bounces: moves from "Needs review" back to "In progress";
  - failed live: tickets labelled `failed-live` (claimed done, broke live);
  - follow-ups: tickets labelled `follow-up` (fixes after the tick).
Tickets loaded already-Done have no history and are skipped.

Run where the agent key is (never printed):
  PLANE_API_TOKEN=... python3 metrics.py [--since 2026-10-01]
Stdlib only, so it runs on the server or the desktop alike.
"""

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE = os.environ.get("PLANE_URL", "https://plane.clockmost.com").rstrip("/")
WS = os.environ.get("PLANE_WORKSPACE", "clockmost")
PROJECT = os.environ.get("PLANE_PROJECT", "FELT")
MOVED = timedelta(minutes=1)


def get(path: str, **params) -> dict:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{BASE}/api/v1/workspaces/{WS}/{path}?{query}",
        headers={"X-API-Key": os.environ["PLANE_API_TOKEN"]},
    )
    for attempt in range(5):  # Plane allows 60 requests/min per key
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code != 429 or attempt == 4:
                raise
            time.sleep(15)
    raise AssertionError("unreachable")


def pages(path: str) -> list[dict]:
    out, cursor = [], None
    while True:
        data = get(path, per_page=100, **({"cursor": cursor} if cursor else {}))
        out.extend(data["results"])
        if not data.get("next_page_results"):
            return out
        cursor = data["next_cursor"]


def when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="only tickets Done on/after this date (YYYY-MM-DD)")
    args = ap.parse_args()

    project = next(p for p in pages("projects/") if p["identifier"] == PROJECT)
    pid = project["id"]
    labels = {lab["id"]: lab["name"] for lab in pages(f"projects/{pid}/labels/")}
    issues = pages(f"projects/{pid}/issues/")

    cycles, bounces, failed, followups = [], {}, [], []
    for issue in issues:
        names = {labels.get(lid) for lid in issue.get("labels", [])}
        title = issue["name"]
        if "failed-live" in names:
            failed.append(title)
        if "follow-up" in names:
            followups.append(title)
        if when(issue["updated_at"]) - when(issue["created_at"]) < MOVED:
            continue  # never touched since it was loaded: no history to read
        moves = [
            a
            for a in pages(f"projects/{pid}/issues/{issue['id']}/activities/")
            if a.get("field") == "state"
        ]
        moves.sort(key=lambda a: a["created_at"])
        started = next((a for a in moves if a["new_value"] == "In progress"), None)
        finished = next((a for a in reversed(moves) if a["new_value"] == "Done"), None)
        n_bounce = sum(
            1
            for a in moves
            if a["old_value"] == "Needs review" and a["new_value"] == "In progress"
        )
        if n_bounce:
            bounces[title] = n_bounce
        if (
            started
            and finished
            and (not args.since or finished["created_at"][:10] >= args.since)
        ):
            days = (
                when(finished["created_at"]) - when(started["created_at"])
            ).total_seconds() / 86400
            cycles.append((title, days))

    print(
        f"Board metrics for {PROJECT}" + (f" since {args.since}" if args.since else "")
    )
    if cycles:
        med = statistics.median(d for _, d in cycles)
        print(f"- cycle time: {len(cycles)} tickets, median {med:.1f} days")
        for title, days in sorted(cycles, key=lambda c: -c[1])[:5]:
            print(f"    {days:5.1f} d  {title}")
    else:
        print("- cycle time: no ticket has gone In progress -> Done on the board yet")
    print(
        f"- review bounces: {sum(bounces.values())}"
        + "".join(f"\n    {n}x  {t}" for t, n in bounces.items())
    )
    print(f"- failed live: {len(failed)}" + "".join(f"\n    {t}" for t in failed))
    print(f"- follow-ups: {len(followups)}" + "".join(f"\n    {t}" for t in followups))


if __name__ == "__main__":
    main()
