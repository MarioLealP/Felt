# WP-42: the Felt app (plan, 2026-10-02)

Status: **planning** — decisions are taken with Mario one at a time (log at
the bottom); nothing is built until the plan is agreed.

Spec: [`felt-usefulness-plan-2026-09-26.md`](../felt-usefulness-plan-2026-09-26.md)
Track E + the 2026-09-26 decisions. Mario: "we might need an actual app style
for her, cuz I might miss her saying that but would come in handy to see
written"; "server holds the app, desktop and phone for presentation layer … a
separate log for the app, like chat which is the whole chat, then her diary
from the WP, the daily brief etc".

## What exists today (inventory 10-02)

- **felt-dashboard** is already a fork of `clockmost-frontend-template` (React
  19, Vite 8, TS 7, Tailwind 4, oxlint/oxfmt, Vitest, pnpm, Endfield CSS). It is
  one chat view (`App.tsx` 243 LOC), no router. felt-tray serves its `dist/` on
  localhost inside a pywebview (WebView2) window. Not hosted anywhere.
- It calls **felt-animation on `127.0.0.1:8421`** directly (`/tone`,
  `/request_started`, `/reply_ready`, `/reply_append`) — only works on the
  desktop.
- It bakes **`VITE_FELT_CORE_TOKEN` into the bundle** — fine on localhost, must
  never be served from the server.
- Session id is a constant `"dashboard"` (matches felt-tray's `api_client.py`).
- **felt-core** (FastAPI, SQLite `felt.db`) already has: chat (`/v1/text-chat`,
  `/v1/voice-chat`, chunked replies), `GET /v1/history` (role+content only, no
  ids/timestamps/kind, max 100), diary + self-memory read/edit/delete, the
  `proactive` table, `ntfy_events`, `pending_emails`, alarms. Auth: bearer
  token everywhere except exact SSO-gated paths (`_SSO_GATED`, the
  shopping-list pattern from WP-55).
- **What she says is only partly kept:** chat replies and spoken screen/event
  remarks land in `messages` (mixed in with chat, told apart by string match);
  proactive lines sit in `proactive`; email "you have mail", alarm firings and
  outgoing ntfy pushes are **not stored**; bubbles and ambient fillers aren't
  logged at all. There is no single typed log of "everything she said".

## Shape (proposed)

```
phone / desktop browser ──SSO──┐
felt-tray window (WebView2) ───┤   Caddy  felt.clockmost.com
                               ├── /app/*      → the app's static build
                               └── /v1/app/*   → felt-core (SSO-gated, X-Authentik-Username)
desktop-only bits (lip sync / tone) → the tray window's local bridge, never the server
```

- **Backend = felt-core.** The app's data already lives there; no second
  backend or proxy. New endpoints under `/v1/app/…`, gated by SSO exactly like
  the shopping list (Caddy forward-auth + felt-core trusting the header only on
  those paths). Tray/desktop clients keep using the bearer token.
- **Front-end = felt-dashboard grown into the app** (same repo, house stack):
  router, tabs, mobile-first layout, Endfield (true black on the phone).
- **No secrets in the bundle.** The served build has no token; SSO is the lock.

## Building blocks

1. **The log ("feed") in felt-core.** One typed table for everything she
   says or surfaces: kind (`chat`, `remark`, `proactive`, `email`, `alarm`,
   `alert`, `reminder`, `brief`, `agent`…), text, source ref, created_at,
   read_at, dismissed / snoozed_until. Every place she speaks writes a row
   (including the ones lost today). Chat keeps `messages`; the history API
   gains ids, timestamps, kind and paging.
2. **Live updates:** one server-sent-events stream (`/v1/app/stream`) so an
   open app shows new lines without polling.
3. **Tabs:** Chat · Feed · Diary · Briefs (later: Reminders, Agents).
   - Chat: the whole conversation, typing (and mic on desktop).
   - Feed: unprompted lines + alerts, read/unread, per-card actions (dismiss,
     snooze, "not interested", open in Gmail / tell me more / draft reply when
     WP-43 lands).
   - Diary: her diary + self-memories, with the edit/delete/pin/veto WP-26
     deferred here.
   - Briefs: the morning-card archive (filled by WP-45).
4. **Tray window:** loads the hosted app instead of the local build; the
   lip-sync/tone calls go through a small pywebview bridge only when inside
   the tray, so the phone never needs them.

## Phases (each ends with something Mario can use)

| Phase | Delivers | Proof |
|---|---|---|
| A | Hosting + SSO + router skeleton; Chat tab moved; tray window points at it | chat works from the phone and from the tray window |
| B | The log table + writers + Feed tab + live stream + read/unread/actions | a day of her lines readable, nothing she said missing |
| C | Diary tab (read, edit, delete, pin, veto self-memories) | Mario edits an entry from the phone |
| D | Briefs tab shell + phone polish (installable app, true black) | opens like an app on the phone |

Mockups go through the review app before phase A's UI is built.

## Open decisions (one at a time, in this order)

1. Hosting shape: app served at `felt.clockmost.com/app` from its own small
   static container vs. bundled into felt-core.
2. The tray window: hosted app vs. keep the local build.
3. Feed scope: which kinds go in, whether Chat also shows remarks, what
   "read" means.
4. Editable lists (game news, email noise): built here as a framework, or in
   WP-43 / WP-49 when each list exists.
5. Phone: installable app (PWA) or a bookmarked page.
6. Briefs tab: now as an empty shell, or with WP-45.

## Decisions log
