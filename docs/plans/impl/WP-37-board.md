# WP-37: the board (Plane)

Spec: [`felt-usefulness-plan-2026-09-26.md`](../felt-usefulness-plan-2026-09-26.md), Track A
plus the 2026-09-26 decisions ("Tickets are what Mario reads", "Felt has an
overview of the board").

## What exists (2026-10-02)

- **Plane CE v1.4.2** (open source, AGPL, self-hosted) at
  **https://plane.clockmost.com**, VPN-only. Stack: `clockmost-infra`
  `projects/plane` (13 containers, ~1.2 GB RAM). Login is **Sign in with
  Gitea** only (Gitea is SSO); password, email-code login and sign-up are off.
- Workspace `clockmost`, project **FELT**: one waterfall board, columns left
  to right: Polish pile · Backlog · Parked · Ready · In progress · Needs
  review · Done · Dropped.
- **Ticket form:** What / Why (Mario's quote) / Where / Accept (checkboxes) /
  Depends / Evidence / Spec link. Done tickets keep only What / Where /
  Evidence / Spec. Depends are also real "blocked by" relations.
- Labels: `wp`, `polish`, `server`, `mario`, `idea`, plus `failed-live`,
  `follow-up` (counted by metrics) and `agent-ok` (work agents may take, WP-52).
- `tools/board/tickets.py` holds every ticket in board order, and
  `load_board.py` builds the project in plane-api's Django shell (refuses to
  run twice). It's the record of the migration; after 10-02 **the board is the
  source of truth**, not these files.
- **Felt:** felt-core skill `board_status` ("what's in progress / waiting for
  me / next / on the polish pile?"). It refuses any request that isn't a GET
  before it's sent. Key `FELT_PLANE_API_TOKEN` in felt-core's sops.
- **Agents:** `PLANE_AGENT_TOKEN` in `projects/plane/admin.sops.env` (also the
  god-mode admin login). Plane's MCP server (`makeplane/plane-mcp-server`,
  `PLANE_BASE_URL=https://plane.clockmost.com`) can use it.
- **Metrics:** `tools/board/metrics.py` (stdlib, read-only): cycle time
  (In progress → Done), review bounces (Needs review → In progress), and
  `failed-live` / `follow-up` counts. Run with `PLANE_API_TOKEN` set.

## Rules

- Only Mario, or Claude after Mario's live review, moves a card to Done.
- Felt never moves cards.
- A claim of done that breaks live gets the `failed-live` label; a fix after
  the tick is its own ticket labelled `follow-up`.

## Notes from implementation

- **Why Plane, not Gitea:** Gitea 1.27.3 has project boards but no API for
  them (nothing to read columns or move cards), so neither Felt nor agents
  could use them. Mario asked for a proper AI-friendly board; the AI-native
  ones were one-person projects or sunsetting (Vibe Kanban), so Plane, which
  has an official MCP server. Mario: "Plane sounds good"; "I want open source
  free" (CE is AGPL, no licence).
- **Celery worker:** upstream starts one process per CPU (12) and blew its
  768 MB limit; capped with `--concurrency=2`.
- **Login config lives in Plane's DB** (`InstanceConfiguration`), not only
  env: the Gitea client id/secret were written there from the env and the
  cache cleared (`manage.py clear_cache`), otherwise the public config stays
  stale.
- **Pushback, accepted by Mario ("you are free to push back"):** no README
  generated from the board. Mario reads tickets, so the board is the single
  truth; the README points to it. A synced copy would bring back the drift
  this WP exists to end.
- **Open:** the throwaway Gitea key `plane-oauth-setup-1790954288` (scope
  write:user, never printed) still needs deleting in Gitea → Settings →
  Applications (Mario: "Skip 1"; the agent can't delete it).
