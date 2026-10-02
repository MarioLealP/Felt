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

## Functionality list (draft, to go through with Mario)

Mario 10-02: "we need to make an actual functionality list and other stuff
before that kind of decision". **P** = already promised in the plans
(source in brackets), **S** = my suggestion, to keep or cut. Owner WP in
brackets when it isn't WP-42 itself.

**1. Chat**
- 1.1 P The whole conversation, scrollable back through all of it, with times ("chat which is the whole chat").
- 1.2 P Type to her from phone and desktop.
- 1.3 P Mic on the desktop (exists today).
- 1.4 S Voice from the phone: hold to talk, she answers in text, and optionally in her voice.
- 1.5 S Search the chat history.
- 1.6 Open: do her unprompted remarks show in Chat too, or only in the Feed?

**2. Feed** (everything unprompted, so nothing she said is missed)
- 2.1 P One timeline: remarks, screen reactions, proactive lines, email mentions, server alerts, reminders, smart-home actions, game news, agent reports, board cards moving to Needs review (Track E, WP-37).
- 2.2 P Lines she skipped saying land here: repeats she held back, and everything during quiet mode, plus the catch-up (personality plan, WP-46).
- 2.3 P Read / unread, to catch up after calls and games; an unread count.
- 2.4 P Per-card actions: dismiss, snooze, "not interested" (feeds the email noise list).
- 2.5 P Email cards: open in Gmail, tell me more, draft a reply; never send (WP-43).
- 2.6 S Filter by kind (only alerts, only email…).
- 2.7 S New items appear live while the app is open.

**3. Daily briefs**
- 3.1 P An archive of the morning cards, today's on top (WP-45 fills it).

**4. Diary**
- 4.1 P Her diary, day by day, readable (WP-26).
- 4.2 P Edit or delete an entry (WP-26 deferred this here).
- 4.3 P Her self-memories (opinions, running jokes): view, edit, delete, pin, veto (WP-26, personality plan).

**5. Lists and settings**
- 5.1 P Editable watched-games list for game news (WP-49).
- 5.2 P Editable email noise rules (WP-43).
- 5.3 S What she knows about Mario (the facts she remembers): view, edit, delete.
- 5.4 S The shopping list inside the app (today it's a separate phone page).
- 5.5 P/later Reminders list (WP-46) and an Agents tab (WP-52).

**6. Controls from the phone**
- 6.1 P Quiet mode on/off with a timer (WP-46).
- 6.2 S Hush / stop her talking, from the phone.

**7. Status**
- 7.1 S Is she up: desktop app, animation, voice, brain.
- 7.2 S Her mood right now.
- 7.3 S The board at a glance (what's waiting for review), from WP-37.

**8. Other requirements**
- 8.1 P Desktop (the tray window) and phone, same app.
- 8.2 P Served from clockmost, SSO login, data stays in felt-core, nothing new goes to the cloud.
- 8.3 P Endfield design, true black on the phone.
- 8.4 Open: reachable only on VPN/LAN (like now), or from anywhere.
- 8.5 S Phone notifications stay with ntfy; the app doesn't add its own.
- 8.6 S Only Mario uses it (no other accounts).
- 8.7 Open: installable on the phone (opens like an app) or a bookmark.

## Shape (proposed, after the functionality list is agreed)

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
