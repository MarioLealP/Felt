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
- **2026-10-03, asides expire after 6 hours** (Mario: "yes"). Only the Talk
  view: remarks stay stored. Mario also offered "do it in general to clean up
  the database"; Claude pushed back: the whole felt.db is 2.3 MB after three
  weeks, and old remarks feed the diary, her self-memory and the Margins
  page, so deleting them would make her forget for no space gained. Only
  truly dead rows are cleaned (aside picks from earlier batches).
- **2026-10-03, asides in Talk shipped (felt-core 571cd61, felt-app
  930dc68), accepted without a live check** (Mario: "I can't Check rn so feel
  free to keep building"). To look at on the phone once she has made some
  remarks: how the two asides sit under the transcript, the "↳ re:" bar.
- **2026-10-03, tray window on the hosted app (42.2 d, felt-tray b1207d5).**
  The tray served a local copy of felt-dashboard from localhost, which broke
  with the app rewrite (it calls /v1/app on its own origin). Now the window
  loads felt.clockmost.com/app/ (derived from felt-core's URL), keeps its
  cookies so SSO survives restarts, and exposes one bridge method,
  `text_chat`, which sends the line via felt-core /v1/text-chat with the
  tray's token and hands the reply to felt-animation, so she speaks it.
  Answering an aside goes straight to /v1/app (silent at the desk) until the
  bridge carries `answering` too. Takes effect on the next tray restart.
  **WP-42.2 → Needs review** on the board.
- **2026-10-03, WP-42.3 built (Mario: "Keep rolling"; "nothing is mandatory,
  you can rethink the whole system"; "no need to fear big refactors while app
  isn't mature").** Rethought the log: instead of a second "feed" table,
  every line lives in `messages` with a `kind` (chat / remark / event /
  proactive / email / alarm) plus source_ref and read / dismissed / snoozed.
  Talk, the Margins, the asides and her own context are filters on one
  table; the old remark test (matching message text against the remark
  tables) is gone, used once by the migration (live DB backed up first:
  data/felt.db.pre-kinds-20261003). Pushes, new-mail lines and alarms, which
  used to vanish (expired queue items, ntfy only), are now her lines and in
  her history. Margins API (list, unread count, mark read/dismiss/snooze,
  exact SSO paths); live updates as server-sent notices (the app refetches;
  no data in the stream); the Margins page (source labels, day breaks, read
  after 1.5 s on screen, answer her / later 3 h / dismiss, unread on the
  flag); ink "seen" server-side so a mark plays once across devices. All
  existing lines were marked read once (1,198) so the count starts at 0.
  felt-core bd1e579, felt-app 6550955. Not live-checked yet.
  Found on the way, parked for Mario: her chat context (last 20 lines)
  includes her remarks, so at the desk the conversation is pushed out by
  her own screen comments; now a one-line fix with `kind`, but it changes
  her behaviour.
- **10-03 — Her context is the conversation, plus a note of what she said on
  her own (Mario: "yes and make sure she knows the remarks so she repeats
  herself less").** Chat reads the last 20 conversation lines (kind chat)
  plus one system note listing her 6 most recent unprompted lines (remarks,
  event lines, pushes, mail; last 6 h), so he can bring them up and she
  doesn't repeat them. Remarks and event lines get the same "already said"
  list (8 lines), now from every kind of her lines, not only screen remarks.
  felt-core 7d0f424.
- **10-03 — Left is hers, right is his, across the whole app** (Mario: "dont
  do top of the page, just do left side messages are hers, right side are
  mine for the whole system"; after seeing Talk: "I like it"). Talk: her
  lines from the margin with the time in the gutter, his right-aligned, 15%
  short of the margin, time after the words; no FELT/YOU labels (screen
  readers still get a name). Replaces "brief on top, her note below" for the
  diary: her note on the left, his brief (WP-45) on the right when it
  exists. Margins are all hers (left); list items sit on the side of whoever
  added them. felt-app 7add3b1.
- **10-03 — She lives on the server; devices are windows and senses.**
  Mario: "the whole she lives on the server is the right way. The link is
  just until we have an app going, there is no reason to build around
  something that will be fixed ... ntfy stuff and spotify and calendar and
  etc still exist even if desktop is closed. So she needs to receive and
  react to those ... dont build around the whole browser". So: no PWA / web
  push work; the hosted link is a stopgap view. The phone app (native
  Android, ex-42.6) replaces ntfy; it can report "he's up" (unlock / sleep
  API). How its notifications travel is decided when we get there (Mario:
  "we cross that bridge when we get there"). Order: first move the senses
  that don't need the desktop to the server (day start from any sign of
  him, song remarks from the server's own Spotify poll, ntfy alerts she
  can react to), then the app. Diary page paused until then.
- **10-03 — Alerts: she is the first responder, rules per alert type.**
  Reread of 09-26 C4 / WP-41 / WP-44 and 10-02 8.5 / 2.8 / WP-58 after
  Claude drifted into "she stays quiet on most alerts" (Mario: "the plan is
  for her to do the first responder to them, along with me getting the
  notifications but on her app itself so I can yeet ntfy since this is just a
  topic thing"). ntfy stays only as the server-side topic; the ntfy app goes.
  - **Notifications pop everywhere** (Mario: "I should get the phone alert
    indepent if im on the pc, or the phone, can pop them everywhere"): every
    alert notifies on phone and desktop alike, wherever he is.
  - **Who handles what depends on the alert type** (Mario: "any cyber
    related stuff should be throwing at you, if its server restarted, then
    she can handle it since there is nothing to handle"): security alerts go
    to Claude for triage (the WP-58 cloud opening, accepted for this);
    benign/expected ones she closes herself; the rest per type.
  - **Her 12B's real ability is unknown** ("i dont know what kind of task can
    she actually handle on her own"): measure on real alerts before giving
    her a class of alerts to handle alone.
  - Next: a catalogue of the real alert types (from the 1,449 stored), each
    with tier, who handles it, and what handling means.
- **10-03 — What she tells him about an alert.** Security split accepted
  ("sounds good"). For every alert she says: is it expected, is there
  anything he can do, who's on it (Mario: "mostly I need her to tell me if
  this is a warning that is meant to be happening and if there is something
  i can do kind of deal, cuz most concerning warnings is something you need
  to handle. Update deployed or Renovate started, is something that needs to
  be told but not acted upon"). Concerning alerts, security or not, are
  Claude's to handle; expected ones are told, never acted on (replaces 09-26
  "info → never"). Catalogue updated: docs/plans/impl/alert-catalogue.md.
- **10-03 — Handing alerts to Claude: A, a headless Claude on the server,
  investigate-only to start** (Mario: "A sounds good, I can open the normal
  Claude app too if needed, the idea is she can interact with you, and i
  interact with her if needed, but if its very serious i will just pop over
  the app so we deal with it together directly"). Felt hands concerning
  alerts to Claude Code running headless under the clockmost-claude account;
  the report comes back to her and to Systems; server changes wait for
  Mario's go-ahead. She talks to Claude, Mario talks to her; for something
  serious Mario joins Claude directly, so each incident's Claude session is
  kept resumable (its session id stored with the incident).
- **10-03 — Organised by WP** (Mario: "The phone app isn't a priority so
  unless we on the phone app WP, just leave it to then, slow steady and in
  order so its well organized"). The alert work lives in WP-44
  (docs/plans/impl/WP-44-server-care.md: intake + rules, her line), WP-58
  (the Claude handler) and 42.5 (Systems page, desktop notifications). The
  phone app stays in 42.6, untouched until then.
- **10-03 — The chain: she warns first, then relays the outcome** (Mario:
  "Double ping, since thats the current model anyway, ntfy hits me, then
  hits me with the resolved. I want to find out when the fire starts, not
  when its already on fire, same ntfy system, she just works as the relay").
  ntfy → her → if it's Claude's she tells Mario straight away ("Claude's on
  it") and hands it over → Claude investigates → his report comes back to
  her → she tells Mario the outcome (fine / needs him) → for something that
  needs him, Mario goes to Claude's session. Two pings by design, like ntfy's
  alert + RESOLVED today. (Claude had suggested waiting for the verdict to
  save a ping; Mario chose to hear when the fire starts.)
- **10-03 — The app must show when it's her that's down** (Mario: "app needs
  to be able to tell if she told me, or if its felt who is down, i need to
  get the ntfy itself to tell me"). Requirement for 42.5 / 42.6: a raw alert
  must never depend on Felt being up. The app gets the raw alerts too and
  pairs each with her line; one she hasn't relayed in a few minutes shows as
  the raw alert, marked as not from her, and "felt-core is down" itself
  comes straight from the server, never through her. Until 42.6 the ntfy
  app keeps getting every raw alert, so nothing changes now.
- **10-03 — 42.5 order: Systems → notifications → Lists → controls card**
  (Mario: "onwards to system").
- **10-03 — Systems page shape** (Mario: "sounds good, but let me click on
  the incident and see further"). Top: a few areas (server, backups,
  security, desktop, laptop, router), a dot each, fine unless an open
  incident needs him; the one that does is circled in raspberry ink with
  handled · ask Felt · details. Below: what happened, newest first, her line
  per incident, Claude's verdict as a small note, expected ones quiet and
  grey. Built from the incidents only (no second source of truth); Zabbix /
  Wazuh linked from details.
- **10-03 — Incident details + Claude's trail now; chatting with Claude from
  the app later** (Mario: "in a perfect world, it would let me hop on the
  claude chat itself if needed but that might be to sketchy"; "I like both").
  Details: her line, Claude's full report, the raw alerts, the session id,
  and his investigation trail (each command and what it showed), read-only.
  Continuing the session from the app = WP-61: not sketchy as such, since that
  Claude stays read-only in its sandbox with the same usage limits; changes
  still go through Mario.
- **10-03 — 42.5 step 1 built: the Systems page** (felt-core 500774f,
  13f2bdb, 6e5b59c; felt-dashboard e221c27; infra 2cbb51f). Overview: the six
  areas with dots, the one needing Mario circled in raspberry ink (drawn once
  per device) with handled · ask Felt · details; history newest first, her
  line + Claude's verdict as a note, quiet ones grey. `#systems/<id>`: her
  lines, Claude's report, his trail (each command + output, collapsible), the
  raw alerts, `sudo felt-responder-join <session>` with copy, Zabbix/Wazuh
  links. "ask Felt" opens Talk answering her alert line; she gets the
  incident's facts and Claude's conclusion with it.
  - Found and fixed on the way: (1) felt-core trusted the SSO header on the
    new routes before Caddy gated them - ~20 min, LAN/VPN only, Caddy logs
    show no use; Caddy now also strips a client-sent X-Authentik-Username
    everywhere else, so a missing path fails closed. (2) The responder's home
    was root-owned (chown hit the DynamicUser symlink), so Claude's sessions
    weren't saved - no trail, nothing to join; fixed. (3) With the push,
    Claude could close an incident before her first line, which then never
    came; now she says both in one line.
- **10-03 — Systems approved** after one fix round (Mario: "it scrolls the
  whole page, instead of just the bottom, so the circled bit stays in the
  middle of the screen" -> areas pinned, only the history scrolls; her ink now
  scrolls with its words, which also fixed marks in Talk; felt-dashboard
  2f40f82). Mario: "Looks great, good job".
- **10-03 — Desktop notifications = the tray's Windows toasts** (Mario:
  "Option1, since eventually we will have the actual presentation layer in
  the desktop like on the mockups right?" - yes: the tray window already shows
  the hosted app, 42.2 d). A toast pops whether or not the app is open; its
  **details** opens the tray's own Felt window at `#systems/<id>`, **handled**
  closes the incident. Laptop and phone stay on the ntfy app until 42.6.
- **10-03 — What pops, by level** (Mario: "Sounds good"): urgent = pop-up
  with sound, stays until closed; high = normal pop-up; default = Systems
  only; low = history only. For the ones that pop, both of her lines pop
  (first word + outcome). Exception: an outcome that needs Mario, or "Claude
  couldn't look", always pops whatever the level.
- **10-03 — Our own pop-up instead of Windows toasts** (Mario: "we might need a
  proper notification system like steam has, instead of the toast since
  windows toasts are kinda finicky and a pain"). A small borderless,
  always-on-top tray window sliding in bottom-right, drawn by the app itself
  (a notice page, so it looks like the notebook and deploys with the app),
  doesn't steal focus, stacks; urgent has a sound and stays, high fades. Limit:
  shows over windowed / borderless games, not exclusive fullscreen (no hooking
  into games).
- **10-03 — Pop-up keys: wanted, combos left open** (Mario: "leave the
  keybinds themselves open for now, since we will need to be sure they dont
  over lap windows nor linux keybinds, but the issue with linux is we need to
  pick the final distro/DE i will be using. Since i dont want to muscle memory
  keybinds then swap"). Built with no combos bound; buttons by mouse until
  then. Claude's draft for later: Ctrl+Alt+D details / A ask Felt / K handled
  / Q close, registered only while a pop-up shows - to be checked, together
  with her existing Ctrl+Alt set, once the Linux distro/DE is picked.
- **10-03 — desktop pop-ups built** (felt-core f52d15f, felt-tray af4fdfd,
  felt-dashboard bfeffb7; ntfy `desktop-read` login, infra 21a07cd, Mario: "I
  allow"). felt-core decides what pops (notices.py, the levels table); the
  tray polls `/v1/notices` every 5 s and shows its own pop-up (popup.py).
  Changed from "drawn by the app": the pop-up is drawn **locally** by the tray
  in the notebook look, because a pop-up that loads its page from the server
  fails exactly when the server is in trouble. Fallback: the tray listens to
  ntfy itself and pops a raw alert ("straight from the server - Felt didn't
  answer") only if felt-core is still down 2 min after it arrived. With
  felt-llm down, urgent/high incidents get a plain line from the same facts,
  so a model outage never silences them.
- **10-03 — pop-ups approved** after two rounds (Mario: "kinda too crowded"
  -> a plain column, no title line; "make it from bottom of the screen, and
  just flex upwards as much as space as it needs" -> each measures itself,
  sits on the bottom edge, stacks up by real height; felt-tray 942bb50).
  Sound: "nice and not too loud". Mario: "much better, good job".
- **10-03 — Lists live** (felt-dashboard 4fe19e9, felt-core c3451ca): add,
  cross off yourself (Mario: "Let me add stuff manually to shopping list, and
  cross it myself"), remove, clear crossed off; her voice edits show at once.
  Mario: "Looks good".
- **10-03 — Two more flags: settings and controls** (Mario: "we might need to
  rethink where the other lists live, they more of a config thing, they can
  have their own flag ... we can easily fit 3 or so more flags"; "Sounds good
  with settings, maybe a controls which has the controls cards and on
  desktop the keybinds?"). Flags: talk · margins · diary · lists · systems ·
  settings · controls.
  - **lists** = real lists only (shopping now, reminders with WP-46).
  - **settings** = things tuned once in a while: games for news (WP-49),
    email noise (WP-43), what she remembers about you, and on the desktop
    the keybinds (all of them, rebindable there; the phone hides them) -
    Mario: "Actually keybinds go on settings makes more sense".
  - **controls** = what's flipped often: her status and mood, quiet mode
    with a timer, hush/stop. Replaces the "tap her name" card (dropped: one
    obvious place beats a hidden gesture).
- **10-03 — Flags flipped to the bottom** (felt-dashboard 306b33a; Mario:
  "Change the order controls then settings, settings always the bottom";
  "flip the whole list and put it near the bottom, it's a better layout for
  phone"): from the bottom up talk, margins, diary, lists, systems,
  controls, settings.
- **10-03 — Controls = two tiles, hide and quiet, HyperOS-style** (Mario:
  "I need quiet and I need hide. So one hides but doesn't quiet her, the
  other hides and quiets her. Like on phone you have the bell for
  notifications and the moon for full dnd. Use the same system it has on
  hyper os. Tap for unlimited, slide for set timer 15 30 1h 8h").
  - **hide**: off the screen, still talks and tells him things.
  - **quiet**: off the screen and silent (cuts her off; unprompted lines
    wait in the Margins). Replaces both hush and the planned quiet mode.
  - Tap = on until turned off; slide = timer snapping to 15m / 30m / 1h /
    8h; the tile shows the time left.
  - Default (Claude's, to confirm): urgent server alerts still pop during
    quiet, like phone DND letting alarms through.
  - How: felt-core holds the two switches (the app sets them from anywhere);
    the desktop tray applies them to felt-animation and reports her real
    state and mood back, so the page is right from the phone too.
