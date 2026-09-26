# Felt usefulness plan — tools, local agents, board, code order

Written 2026-09-26, while quota was running low. **This is a plan only: no
code has been touched and no research done yet.** Each track starts with its
own spike, where the research happens. Mario's brief:

> one big plan that is not for the visual side of felt, but for the useful
> tools of felt, emails, proper HAOS controls … stuff she does on her own, and
> that we can do with local agents, we might also need to rethink openhands
> and 9router, maybe some integration with local agents on that + felt as the
> evil mastermind so we can do some fun coding tasks … I still want a proper
> docs WP are displayed on a jira style board … enforce what why where style
> metrics, sort the code since rn is kinda of a blackbox … proper spike with
> up to date information.

The workflow is the usual one: this whole plan first, then discuss it **one
track at a time**, and only then turn each track into numbered WPs.

## Principles (standing rules carried over)

- **Reaction-first still holds.** "Useful" means things she does *on her
  own*, well-timed and budgeted, not a chatbot waiting for commands.
- **Local-first privacy.** Local data is fetched locally. The cloud only
  sees what the privacy line allows (Google data, alarms, shopping list and
  music are OK; documents, remembered facts and location never).
- **One voice. Gemini on the free tier,** so every cloud call is counted.
- **Local agents do the grind; Claude designs and verifies.** Nothing
  counts as "done" without evidence (the DELEGATION.md rules apply to every
  agent).
- **Rejected features stay rejected:**
  - relaying Home Assistant/ntfy **home alerts** (HA *controls* are fine);
  - OBS auto-clips, the Gemini Live API, pats/drag, and a phone as an
    offload node.

---

## Track A — Board + What/Why/Where discipline

**Goal:** every WP lives on a Jira-style board with enforced fields and
honest status. No more drift between the README, the notes and reality (the
09-24 audit problem).

**Spike A1: pick the board.**
- Candidates:
  - **Gitea's built-in Projects** (kanban): we already self-host it behind
    SSO, and it adds no new service. That fits the "one place" preference.
  - **Plane**, the closest self-hosted Jira clone.
  - Vikunja, Planka and Focalboard.
- Criteria:
  - issue forms with **required** fields;
  - kanban columns plus labels/milestones;
  - an API that agents and Felt can use to read and move cards;
  - Authentik SSO, and a mobile-friendly view;
  - backup inside the existing restic scope.
- Leaning: Gitea Projects, unless required fields or automation fall short.

**Build (after the spike):**
- **One issue per WP**, with an issue-form template whose required fields
  are:
  - **What:** the deliverable, one paragraph;
  - **Why:** the value, with Mario's own quote;
  - **Where:** the repos, files and machines;
  - **Accept:** checkable items;
  - **Depends on**;
  - **Evidence:** links to proof.
- **Columns:** Backlog → Ready → In progress → **Needs review** (Mario) →
  Done / Polish-later.
- **Rule:** only Mario, or Claude after Mario's live review, moves a card
  to Done.
- **The markdown WP specs stay** the long form, and each issue links to
  its spec. The README status table is **generated from the board** by a
  script, never hand-edited again.
- **Metrics per WP:**
  - cycle time;
  - how often it bounced from review back to In progress;
  - how often something was claimed done but failed live;
  - how many fixes came after tick ("follow-ups").

  Report them monthly, or on request from Felt.
- **Migrate the backlog:** WP-01…36, POLISH-BACKLOG, WP-19's deep dive and
  the performance pass.

## Track B — Sort the code (end the black box)

**Goal:** Mario can see what every part of every repo does. Where the code
is disorganised, it gets split, with no behaviour change.

**Spike B1: architecture audit** (read-only), per repo:
- **Size and structure:** files, lines, the biggest files, the module map
  (who imports whom), and the entry points.
- **Known "god files":**
  - `main.gd` (~2.6k lines, plus WP-22/21 additions);
  - felt-animation `server.py` (~2k lines);
  - felt-core `brain.py`;
  - felt-tray `app.py`.
- **Duplication:** e.g. the window enumerator in felt-tray vs WP-23's plan,
  the cursor/geometry mapping (already mirrored once), and the tag lists.
- **Config sprawl:** a `.env` per repo, the server `.env` hand-edited
  outside git, and hardcoded paths.
- **Dead code:** felt-vision (WP-36 wants to retire it), old launchers,
  `test_view` and legacy protocol messages.
- **Test health:** per-module coverage and environment-dependent tests
  (two have already been found).
- **Protocol docs:** the relay README vs the messages actually sent.

**Outputs:**
- a system map: `docs/ARCHITECTURE.md`, covering machines → services →
  repos → modules → messages;
- an `ARCHITECTURE.md` per repo;
- a ranked list of refactors.

**Build (as WPs):**
- **Split the god files:**
  - felt-animation `server.py` into routers (presence, playback, props,
    signals, debug);
  - `brain.py` into routing, privacy, replies and skills;
  - `main.gd` into components (this overlaps WP-35's shared-code work, so
    do it once, there).
- **Tooling:** ruff lint+format, pyright/basedpyright, pre-commit, and
  **Gitea Actions CI** (tests plus lint on every push) per repo. The
  `project-conventions` skill has the baseline.
- **One config model:** `%APPDATA%\Felt\config.toml` on the desktop
  (WP-34), sops on the server, and the Nitro5 manifest.
- **Rule:** refactors go in their own commits, with before/after behaviour
  proof, the same standard as WP-35.

## Track C — Useful skills she does on her own

For each skill the spike answers:
- data source and API;
- privacy class and local/cloud route;
- trigger: proactive or asked;
- speech budget and cooldown;
- what she *never* does (e.g. send email).

**Spike C1: current inventory.** felt-core already has:
- `email_watcher` / `check_email` (Gmail summaries, google_ok);
- `google_calendar`, alarms, the shopping list, weather;
- `zabbix_client` (server health), `poe_trade_cache` (PoE2);
- Spotify, lyrics, `search_documents` (Drive/Obsidian, local-only).

Map what exists, what works and what's half-done before adding anything.

**C2 — Email, smarter:**
- **Proactive triage:** an "important" message (a rules list plus a
  classifier, deterministic and never an LLM deciding silence) gets a
  budgeted heads-up line and a bubble.
- **An optional daily digest** at a time Mario picks.
- **Reply drafts** only on request, saved as a Gmail draft and **never
  sent** by her.
- **"Unsubscribe candidates"** as a weekly nudge.
- Privacy: Gmail is google_ok.

**C3 — Home Assistant, proper controls** (the HAOS VM on clockmost,
`ha.clockmost.com`):
- Use the HA REST/WebSocket API with a long-lived token in sops, and an
  **entity allowlist** (only what Mario exposes).
- Intents: lights, scenes, climate, media players, covers, "goodnight" /
  "gaming mode" routines, and state questions ("is the heater on?").
- Presence tie-ins, **only if Mario wants them:** e.g. `game_start` →
  gaming scene, AFK/BRB → dim.
- **No home-alert relaying** (rejected feature).
- Confirmations are spoken or bubbled; destructive or security actions
  (locks, alarm panels) always need an explicit yes.

**C4 — Other candidates.** Each gets an explicit keep/drop in discussion.
- **PC care:**
  - disk-space warnings;
  - Chocolatey updates available;
  - restic backup status (desktop → server → gdrive);
  - server health from Zabbix, spoken only when something is actually
    wrong.
- **A morning brief in her voice:** calendar, weather, unread important
  mail and today's reminders. This ties into WP-26 (diary) and WP-31
  (calendar heads-up).
- **Focus/pomodoro with her:** she keeps time, goes quiet-ish during focus
  (Mario-triggered, so it doesn't break never-quiet), and cheers at breaks.
- **Reminders captured from conversation** ("remind me after this match").
- **Spotify controls** (skip, volume, "what's this song") via the existing
  client.
- **Game companions:** PoE2 is already WP-29, and Endfield could be added
  (patch notes, events).
- **Local clipboard/file helper:** "what did I copy", or find a file.
  Local-only.
- **A "what was I doing" recap** after AFK, from the diary (WP-26).

## Track D — Local agents, and Felt as the evil mastermind

**Goal:** routine coding grind moves off Claude onto local/self-hosted
agents, and Felt runs the show: she hands out tasks, watches them, reports
back, and teases.

**Spike D1: what we run today, and its fate.**
- **OpenHands** (server; no desktop, E: drive or Godot access), **9router**
  and **smartrouter** (both compose stacks on clockmost; purpose to be
  confirmed), and **agy/Gemini** delegation (read-only wrapper, plus
  Antigravity for write jobs).
- For each: is it used, what does it do, what would it take to keep, and
  should it be merged or retired?
- Candidate end state: **one OpenAI-compatible gateway** fronting WP-36's
  llama.cpp router mode plus cloud providers, with per-caller quotas.
  Evaluate whether 9router or smartrouter already *is* that; a
  LiteLLM-style gateway is the reference point.

**Spike D2: local coding agents, benchmarked on our own tasks.**
- **Candidates** (current versions to be checked in the spike): OpenHands,
  aider, OpenCode, Cline/Continue, goose, and Qwen-Code-style CLIs.
- **Models:** what can realistically run on our hardware:
  - the Nitro5 (6 GB, and busy with voice);
  - the desktop RX 6700 (10 GB, but Smart App Control blocks unsigned
    llama.cpp builds);
  - the server CPU;
  - or free-tier cloud coders.

  Be honest about limits: small local models are fine for
  tests/docs/boilerplate/hygiene, not design.
- **Benchmark tasks from our backlog:**
  - WP-24 hygiene;
  - adding a test;
  - a small refactor;
  - a docs pass;
  - an `.env.example` sync.

  Measure pass rate, time, and how often the result needed fixing.

**Build: the mastermind loop** (after D1/D2):
1. Board issues labelled **`agent-ok`** (Track A) are the only work agents
   may take.
2. Agents work in **branches and PRs on Gitea**, never pushing to main.
   Gitea Actions CI must pass, and a Claude or Mario review merges.
3. **Felt dispatches and narrates:**
   - she picks up `agent-ok` cards;
   - she starts the agent job on the server or Nitro5;
   - she tracks it;
   - she reports in her voice or bubble: "your intern broke the build
     again", "PR #12 is ready for you".

   Budgeted like any other remark, and a tray/dashboard view shows agent
   status.
4. **Fun mode:** Felt proposes small coding challenges or katas, sets
   agents against each other or against Mario, and commentates. It's
   opt-in only, when he's in the mood.
5. **Guardrails:**
   - sandboxed agent workspaces;
   - no secrets in agent reach;
   - rate/quota caps;
   - an audit log per agent run;
   - a kill switch from the tray.

## Research is part of the plan: the spike list

| Spike | Question | Decides |
|---|---|---|
| A1 | Which board tool (Gitea Projects vs Plane vs others)? | Track A |
| B1 | What's actually in each repo; where the rot is | Track B refactor WPs |
| C1 | What skills exist and work today | Track C scope |
| C3 | The HA API, token, entity model and what Mario exposes | HA WP |
| D1 | The fate of OpenHands / 9router / smartrouter; gateway design | Track D infra |
| D2 | Which local coding agent plus model actually succeeds on our tasks | Mastermind WP |

Every spike writes **up-to-date, sourced** findings (current versions and
docs checked at spike time, with a "verified vs inferred" section) into
`docs/plans/spikes/`.

## Proposed WPs and order

Numbering continues after WP-36. The order means Track A goes first:
everything else lands on the board.

1. **WP-37** Board + What/Why/Where issue forms + migrating WP-01…36 +
   the generated README (A1 → build).
2. **WP-38** Architecture audit + the system map + a per-repo
   `ARCHITECTURE.md` (B1).
3. **WP-39** Repo tooling: ruff, pyright, pre-commit and Gitea Actions CI,
   everywhere.
4. **WP-40** God-file splits: felt-animation `server.py`, felt-core
   `brain.py`, felt-tray `app.py`. (`main.gd` stays with WP-35.)
5. **WP-41** Skills inventory (C1) → email triage and digest (C2).
6. **WP-42** Home Assistant controls (C3).
7. **WP-43** PC-care and morning-brief skills (C4 picks).
8. **WP-44** Agents infra: the fate of OpenHands/9router/smartrouter plus
   one gateway (D1). Pairs with WP-36.
9. **WP-45** Local coding-agent benchmark (D2).
10. **WP-46** Felt as the mastermind: dispatch, PRs, narration, fun mode.

The remaining visual WPs (23–33, 35) and WP-34 packaging slot in around
these as Mario prefers. WP-34 stays last.

## Decisions for Mario (discussed one at a time)

1. The board tool: Gitea Projects, or a dedicated Jira clone?
2. Which Track C skills stay: go through the C4 list item by item.
3. Home Assistant: which entities or areas get exposed, and whether any
   presence or game tie-ins happen at all.
4. The fate of 9router, smartrouter and OpenHands.
5. How far agents may go without him: PRs only, or auto-merge for trivial
   `agent-ok` work after CI.
6. Whether "fun mode" is a thing.

## Decisions log

- **2026-09-26, A1 board: Gitea Projects** (Mario: "gitea one is plenty").
  **Tickets are what Mario reads**: short and self-contained, with What / Why
  (his quote) / Where / Accept (checkable) / Depends / Evidence, a few lines
  each. The long WP markdown spec is linked for agents; Mario doesn't need to
  open it ("I don't wanna parse through them, but I'm totally fine parsing
  through a ticket"). The spike still confirms required issue-form fields,
  org-level boards across repos, and moving cards through the API.
- **2026-09-26, C2 email: deny-list plus ambient mentions.** Mario: "it's not
  what makes it worth interrupting, it's what doesn't … the alerts can be
  part of her ambience loop, hey btw have you checked that email from …
  Patreon about ZYX".
  - Skip Gmail's Promotions and Social categories.
  - An editable noise list of senders and patterns: review requests,
    Google account data/security-checkup notices, shop marketing.
    Mario-triggered voice additions ("I don't care about X emails").
  - Every other email becomes an ambient-loop topic: a Gemini one-line hook
    (google_ok), mentioned **once**.
  - Budget: ~1 per hour max, never over call talking, preferably when idle.
  - "Tell me more" gives a summary; "draft a reply" saves a Gmail draft;
    she **never sends** email.
  - No true interrupts by default.
- **2026-09-26, C3 Home Assistant: small, asked-only, extensible.** Today
  it's only lights and a fan (Mario is slowly buying more).
  - Controls by voice/text for an entity allowlist, plus state questions.
  - The allowlist grows as devices are added.
  - Security-type entities (future locks, alarm) need an explicit yes.
  - **No autonomous presence/game tie-ins for now** (no answer given, so the
    default stands).
  - No home-alert relaying.
- **Hardware note for Track D.** Mario is considering a **new GPU + PSU for
  the clockmost server**. If it happens:
  - the WP-36 llama.cpp router (and possibly voice) can move off the
    Nitro5's 6 GB card;
  - local coding agents become realistic;
  - prefer NVIDIA/CUDA, with the PSU sized for 24/7 peak draw plus headroom.

  The D2 spike should include a VRAM-based sizing recommendation (which
  models the agents and chat need), so the purchase can be decided on
  numbers.
- **2026-09-26, C4 PC and server care: via ntfy.** Mario: "She can actually
  react based on ntfy".
  - **Clarifies the old rejected feature:** relaying *home* (Home Assistant)
    alerts stays rejected. **Server/PC alerts over ntfy are allowed.**
  - Felt subscribes to the clockmost ntfy topic(s):
    - **urgent** → a prompt spoken line;
    - **warn** → a casual ambient "btw…" mention;
    - **info** → never mentioned.
  - Disk-space and backup checks feed ntfy rather than Felt polling them
    herself.
  - Chocolatey update notices are skipped (it auto-patches).
- **New item: an ntfy alert hygiene pass on clockmost** (server-side,
  before Felt consumes anything). Mario: "they are a bit too trigger happy,
  since caddy update cuz we getting a new container up is basically the
  same as a world ending event".
  - Severity tiers across `clockmost-notify.sh` callers (healthcheck,
    deploy, backup, prune, maintenance).
  - Expected-event suppression (deploy-caused Caddy reloads and container
    restarts, the Monday reboot, prune windows).
  - Dedupe and cooldown for flapping checks.
  - Proposed as its own WP ahead of the Felt ntfy consumer.
- **2026-09-26, C4 morning brief: yes, spoken + written.** Content:
  - today's calendar and weather;
  - the count of noteworthy emails;
  - reminders;
  - overnight urgent/warn alerts.

  About 20 s, once a day, triggered by the first activity after the night.
- **New Track E: the Felt app (a written feed).** Mario: "we might need an
  actual app style for her, cuz I might miss her saying that but would come
  in handy to see written".
  - A timeline of everything she said or did:
    - remarks;
    - brief cards;
    - email mentions (open in Gmail / tell me more / draft reply);
    - ntfy alerts;
    - reminders;
    - HA actions;
    - Track D agent reports.
  - Read/unread for catching up after calls and games. Per-card actions:
    dismiss, snooze, and "not interested" (which feeds the email noise
    list).
  - Chat lives in the same app.
  - Built on the existing felt-dashboard (React) and felt-tray's Felt
    window, using the clockmost front-end stack and the Endfield design
    language.
  - Open question: desktop-only, or also reachable from the phone (via
    clockmost + SSO)?
- **2026-09-26, Track E hosting and structure.** Mario: "server holds the
  app, desktop and phone for presentation layer … a separate log for the
  app, like chat which is the whole chat, then her diary from the WP, the
  daily brief etc".
  - The app is **served from clockmost** (next to felt-core, behind
    Authentik SSO). The desktop (Felt window) and phone are presentation
    clients only.
  - **Separate logs:**
    - **Chat** (the full history, plus typing to her);
    - **Feed** (unprompted remarks, email mentions, alerts; read/unread and
      actions);
    - **Daily briefs** (an archive of the morning cards);
    - **Diary** (WP-26);
    - later: Reminders and Agents (Track D).
  - Data stays in felt-core's store on the server. The privacy line is
    unchanged: nothing new goes to the cloud just because it's displayed.
