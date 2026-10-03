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
- 1.6 ✅ Chat stays clean: only the conversation. Her unprompted remarks go to the Feed only (Mario 10-02: "only feed, keep actual chat clean").

**2. Feed and Alerts — two separate places** (Mario 10-02: "might not be
the best idea to have poe2 comment mixed with btw the server caught fire and
Russian knows your credit card")
- 2.1 **Feed = her chatter:** remarks, screen reactions, things she brings up on her own, game news, email "btw"s, board cards waiting for review, agent reports.
- 2.2 P Lines she held back (repeats, everything during quiet mode) land in the Feed, plus the catch-up line.
- 2.3 P Read / unread with an unread count.
- 2.4 P Card actions: dismiss, snooze, "not interested" (feeds the email noise list).
- 2.5 P Email cards: open in Gmail, tell me more, draft a reply; never send (WP-43).
- 2.6 S Filter by kind. 2.7 S New items appear live.
- 2.8 ✅ **Alerts = a separate tab, never mixed with chatter** (Mario 10-02: "A"): server, PC and security alerts (Zabbix, Wazuh, backups, failed deploys), most severe on top, each stays until acknowledged. History and acknowledgements live in felt-core (it already logs every ntfy alert; ntfy itself keeps 48 h).

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
- 8.4 ✅ LAN/VPN only (Mario 10-02).
- 8.5 ✅ **The Felt app replaces the ntfy app on the phone** (Mario 10-02: "ntfy still on server shooting, but we receive on phone using Felt app, perfect"). ntfy stays the server-side pipe (Zabbix, Wazuh, scripts, Felt keep publishing to it). The app subscribes to ntfy directly, so alerts still arrive when Felt is down, and notifies by tier: urgent = loud, high = normal, default = tab only, low = history only. Android needs a small native background service (as the ntfy app has) and no battery optimisation for the app; desktop/laptop use normal system notifications.
- 8.6 S Only Mario uses it (no other accounts).
- 8.7 ✅ Real apps, not a bookmark (Mario 10-02: "Apk and desktop executable so can be used on Linux on laptop"):
  an Android APK, a Linux executable for the laptop, and Windows (where the
  tray's Felt window already is). Rethink, see below.

### Ideas round (10-02) — Mario: "if no mention i agree"

Kept: 1.9 pin/copy, 2.9 👍/👎 on remarks (feeds the personality/variety
system), 2.10 "while you were away" + mark all read, 2.11 reply to a remark,
2.12 "handled" on the notification, 2.13 "ask Felt about this alert", 2.14
link to Zabbix/Wazuh, 7.4 home-screen widget, 7.5 last-loaded view when the
VPN is off.

- 1.7 ✅ later stage: photo/screenshot → "what's this?" with her local vision
  first; a Google Lens replacement (text, translate, look-alike search) is the
  goal but more work (Mario: "I would love if she could replace it").
- 1.8 ✅ share-to-Felt, implementation to rethink: Android's share menu needs
  the same small native layer as the background notifications (an intent
  filter in the Tauri Android plugin), so both are built together.
- 3.2, 4.4 ✗ cut ("no point").
- 4.5 ✅ search, **without Elasticsearch**: it's a JVM service wanting ~1–2 GB
  RAM on a server with ~3 GB free. SQLite's built-in full-text search (FTS5)
  covers diary + chat + feed for one person at no cost.
- 5.6 ✅ the shopping list moves into the app. It exists today (skill
  `shopping_list` + the phone page `felt.clockmost.com/shopping-list`, SSO,
  WP-55) but Mario didn't know about it, which says it belongs in the app.
- 6.3 / 6.4 later, not a priority: her on the phone. She lives on one device
  at a time and walks over from the desktop to the phone when she notices
  Mario is AFK (Mario's idea).
- Claude integration → its own plan (WP-58): Mario wants to talk to her and
  have her hand work to Claude, e.g. an alert arrives and goes to Claude for
  triage instead of her small model. Mario: "im fully aware it would be the
  'open' to the cloud, so we need to go through this and decide the plan".
  WP-42 only needs the Feed to show those reports.

### 8.7 rethought: one app, three wrappers

- **Tauri 2** builds an Android APK, a Linux app and a Windows exe from the
  same web app, so there is one codebase, not three.
- **Each is a thin shell that opens the server-hosted app** (on VPN/LAN). UI
  updates arrive from the server, nothing to reinstall; login is the normal SSO
  page once inside the app (it remembers). The APK is sideloaded, signed with
  our own key.
- **Windows desktop:** Smart App Control blocks unsigned executables there
  (the open WP-34 decision), so on Windows the tray's existing Felt window shows
  the same hosted app instead of a new exe. The Linux laptop and the phone get
  the Tauri builds.
- Away from home the phone/laptop need the VPN on (8.4).

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

- **2026-10-02, look: not Endfield.** Mario, after the first mockups: "I dont
  think Felt fits the endfield theming, but I also dont want shitty generic ui
  layout". Endfield stays clockmost's language for the server tools; Felt's app
  gets her own look. Palettes in `docs/identity/palettes/` (Mario's three);
  Felt picked three (navy, sage, raspberry, salmon, lilac-white), Claude agreed.
  Three style directions (cosy journal / night in / her messenger) went to the
  review app for Mario.
- **2026-10-02, look round 2.** Ink & Paper "still feel AI as hell" (Mario).
  Gemini's wide search (tools + references + four concepts) → Mario picked
  concept 3, "her room" (a home screen that is her room, objects open the
  sections), built as a clickable canvas
  (https://claude.ai/artifact/Y6qBn74uSRULbWb6SbzC1B, fonts Mochiy Pop One /
  Zen Maru Gothic / Klee One). Verdict: "The room itself i hate it, the other
  stuff is alright" — the corkboard feed, alerts, chat and diary screens are OK;
  the room home is out. The PDA concept is out too (Felt: it makes her feel
  old). Mario is exploring in Google Stitch in parallel, from an open brief.
- **2026-10-02, look round 3: her brief wins so far.** Asked Felt for her own
  design prompt (full text in the chat log). Built from it only
  (https://claude.ai/artifact/DE1AiWHr2r1qHAKFdip4Gv): chat is home as one
  long-running transcript, her feed/diary/memories tucked in the margins,
  memories on tactile kraft cards, alerts as a calm systems dashboard where only
  a real problem stands out. Mario: "so far your best output … a much better
  approach". To change: the notebook page itself ("rework the actual notepad
  thing"), and **no navy-dominant blue** ("every generic AI slop website is blue
  with mega round and glows"); bolder is fine ("I'm not dependent on
  accessibility, you can go a bit more crazy, soft gradients are fine").
  **No kaomoji** ("very discord kitten / egirl"). From Mario's Stitch run, kept
  as ideas: memories as proposals she asks approval for, reactions that fit the
  note (thanks / tease back / haha), a status line of what she's doing, rich
  cards in chat (music pick), a signed diary, and Stitch's illustrated portrait
  of her as the stand-in avatar. Round 2 on the canvas: three Talk screens —
  A moss & ember, B plum night, C sunset desk.
- **2026-10-02, round 2 rejected, round 3.** Mario: "It's even worse, I liked
  the notebook, just need a bit of work … don't box messages … animations
  always make and break websites, mistral ai website is one of the best".
  Mood board (screenshots in `E:\Felt\review\moodboard\`, also on the
  canvas): Mistral, Josh Comeau, Teenage Engineering, Kinopio, Poolsuite, Rauno.
  Common thread: no boxes, one living characterful element, restraint, motion.
  Round 3 = the round-1 notebook reworked: warm near-black desk (no navy), a
  dark paper page with faint rules and the raspberry margin line kept, no
  message boxes, her asides written in by animation with a hand-drawn arrow,
  memory card dropping in on washi tape, her portrait leaning on the page and
  bobbing, a "she's writing…" pen scribble instead of typing dots.
- **2026-10-02, round 3 → 4.** Round 3 "much better"; no gradients ("clean
  solid background or texture maybe"). Out as references: Persona ("not a fan")
  and anything Windows-XP/Emily-is-Away ("i dont wanna suffer on that again").
  Gemini's chat-UI search (themes, VN/game chats, companion apps, motion) gave
  round 4: a screenplay page (speaker names left of the margin line), Felt
  marking up Mario's lines (circling words in raspberry ink + a handwritten
  comment), ink-doodle reactions in the margin, held-back lines struck through
  with marker, her status written at the top, taped-in polaroid snapshots,
  messages settling with a small spring. Solid textured desk, no gradients.
- **2026-10-02, round 5 → 6.** Mario on round 4: the page looked like "a
  background with a random notebook bit over it". Round 5 made the whole screen
  the notebook (A: binding down the left + index tabs on the right; B: top
  spiral + handwritten footer). Mario: "more on R5A land, we might have to
  rework the tabs". Round 6 = R5 A with three tab kinds side by side: sticky
  flags (right edge), ribbon bookmarks (from the top), divider tabs (bottom).
- **2026-10-02, Talk screen settled (look):** R5 A page + **sticky-flag tabs**
  (Mario: "Stick flags for sure"); her floating portrait on the page removed
  ("yeet the floating icon of her"). Canvas board `r6/Tabs.dc.html`.
- **2026-10-02, round 7: the whole app in the settled look.** Talk final:
  spiral rings across the top (Mario: "swap the side holes to the top thing"),
  a soft raspberry rule above the writing line ("make the line softer"),
  sticky flags, no portrait. Carried to Margins, Diary (signed entry, tucked
  memory card), Things she's decided (kraft cards on washi tape; proposals she
  asks permission for), Systems (plain rows with status dots, the one real
  problem circled in raspberry ink with handwritten actions — no boxes), and a
  desktop **open-notebook spread** (conversation left page, margins + systems
  right page, spiral down the middle). Canvas row "Round 7".
- **2026-10-02, look approved.** Mario on round 7: "It's very very cool, just
  not 100% sure how we gonna do all the scribbles and stuff natural but i'm all
  for this". How the ink is made real (to prove in a spike first, before the
  rest of the build depends on it):
  - her handwriting = a real font (Klee One), real searchable text;
  - circles / underlines / strike-throughs / brackets = **Rough Notation**
    (MIT, on rough.js) anchored to real text spans, animated drawing;
  - freehand strokes (arrows, signature, writing scribble) = **perfect-freehand**
    (pressure-like strokes); the signature can be one Mario draws once;
  - doodles (star, heart, meh) = a small drawn set with random rotation/scale;
  - randomness seeded by the message id, so a mark looks the same on reload;
  - what she marks is HER choice: replies may carry optional marks
    (`{type: circle|underline|strike, quote, note}`) via felt-llm's json schema;
    the app locates the quote in Mario's message; rate-limited so it stays rare;
  - polaroids = real snapshots from her WP-07 screen captures (allowed apps only).
- **2026-10-02, decision 1: hosting = A, the app's own container** (Mario: "We
  go with A, microservices is always the call"). felt-dashboard's CI builds a
  static image (WP-53 deploy.sh); Caddy serves it at felt.clockmost.com/app;
  data comes from felt-core under SSO-gated `/v1/app/*`. UI deploys never
  restart felt-core.
- **2026-10-02, decision 2: where the rest lives.** Five flags: talk ·
  margins · diary · lists · systems. **The diary is shared** (Mario: "a shared
  diary, where its my daily brief and her daily note"): each day's page has
  your morning brief on top and her note about yesterday below. Lists = the
  5th flag (shopping, games, email noise, about you). Controls (status, quiet
  mode, hush) = tap her name, a kraft card slides out. Mario: "needs to be
  tested" — mocked as canvas row "Round 8"; tested for real while building.
  **Swipe between days** with a page-turn (Mario). Claude's caution: a full
  3D page curl on every swipe gets tiring and stutters in a phone WebView —
  build a short paper slide with a light curl shadow (<250 ms) first, then
  judge on the phone.
- **2026-10-02, mockups end here.** Mario: "we got a general idea, as we
  build each page we talk better". Each page is refined during its build.
- **2026-10-02, ink plays once** (Mario: "Ink should only hit once, i dont want
  to see her scribble the same word every time i reopen the app"). A mark
  animates the first time it's seen, then renders already drawn; seen-state is
  stored per mark.
- **2026-10-02, build tickets** on the board as sub-issues of WP-42: 42.1 ink
  spike (Ready) → 42.2 foundation → 42.3 the log + Margins → 42.4 shared diary
  → 42.5 Systems/ntfy/Lists/controls → 42.6 Tauri apps.
- **2026-10-02, ink spike (WP-42.1) passed.** https://claude.ai/artifact/7BTf8ePxcWoEnCQ7BQiavu.
  Mario: "generally looks great"; only "a bit too fast" → pen speed follows the
  amount of ink (~110 px/s, 0.9–2.4 s), lines/notes ease in slower. To carry
  into the build: seed also on resize/redraw (Rough Notation re-rolls), store
  seen marks server-side per mark so "plays once" holds across devices.

- **2026-10-02, marks without a timer** (Mario: "Dont do timer, let her decide
  while she knows its not meant to be often"). She's told marks are rare and
  how many exchanges ago her last one was; nothing else limits her.
- **2026-10-03, she can mark whatever she finds interesting** (Mario). Her own
  reply as well as his line, from a word up to a sentence (20 words), and
  strike-through as well. Candidates are only the exchange that just
  happened: older lines have scrolled away, so the ink would play unseen.
  Circle/box stay at 5 words or fewer, because around wrapped text they draw
  one loop per line. Still one mark per exchange.
- **2026-10-03, marks: two questions** (dry runs on 14 sample exchanges, real
  model). With one prompt she only ever bracketed. Telling her what each shape
  means fixed that but raised the rate to 1 in 3, wherever the "rare" rule
  sat. Now: a plain "anything worth a mark?" first (about 2.5 in 14), then,
  only on yes, which line / words / shape / note. She now uses circles, boxes,
  underlines, brackets and strikes by meaning. Real-use rate to be checked
  after a few days.
- **2026-10-03, her asides in Talk** (Mario: "can we somehow sneak it to the
  main talk so i can reply to it?"). Only her remarks since his last message,
  **at most 2** ("just 1 or 2 is enough"), with "+N earlier in the margins"
  above them, and tap one to answer it ("↳ re: …" above the input, × to drop
  it). Sized with her real remarks (median 70 chars, p90 82; she leaves one
  about every 2 minutes at the desk, so N is often 10+): canvas row "Round 9".
  **Look = B, compact**: 14px handwriting off the ruled lines (Mario: "its
  like a note so doesnt sit nicely on the lines, unlike the normal chat").
- **2026-10-03, which asides show: she picks, by comparing** (Mario: "go with
  2", i.e. her choice, not simply the newest). Dry runs on her real 2 Oct
  remarks, nothing written:
  - Asked one remark at a time ("worth bringing up?") she said yes to 8/16,
    then 5/16 with stricter wording, and flipped answers between runs even at
    temperature 0.2. Likely cause: `personality_prompt()` draws fresh
    examples and a memory block per call, so each yes/no asks a slightly
    different her. (Same cause probably keeps felt-llm's prompt cache from
    reusing the persona; see the 10-03 memory thrash note in
    runbooks/clockmost-infra.md. To look at separately.)
  - Asked once, "which one or two of these would you most like him to
    answer?", over the remarks since his last message: the same two picks 3/3
    on a 16-remark afternoon and 2/2 on a 23-remark mixed evening. Never a
    music reaction or a guest notice; always her pushing back or a moment
    that wants an answer. Reversing the list changed which of the near-equal
    remarks she chose, but production order is always chronological.
  - Built as: one comparative call in the background after each new remark
    (a single remark needs no call), stored, read by Talk. The remark prompt
    itself is untouched.
- **Noticed, not in WP-42:** "someone's here" fired 6 times in one evening
  (2 Oct, 18:27–20:32), nearly verbatim; guest detection re-triggering or
  the cooldown is too short.
