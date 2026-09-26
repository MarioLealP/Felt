# WP-38 — Architecture audit: system map + ranked cleanup list

Read `00-implementer-context.md` first. This WP was **pulled forward** ahead
of WP-23 (decision, 2026-09-26 usefulness-plan log) — it has no hard
dependency on the board (WP-37); its outputs become board tickets once WP-37
exists.

## What

Five parallel repo audits (felt-core, felt-animation, felt-character-assets,
felt-tray, felt-dashboard — each producing that repo's own `ARCHITECTURE.md`)
plus the pre-existing `docs/architecture/felt-vision.md`, `felt-voice.md` and
`umbrella-scripts.md` notes, synthesized into three documents:

1. `E:\Felt\docs\ARCHITECTURE.md` — the system map (machines → services →
   repos → modules → messages), with one data-flow diagram each for a voice
   reply, a screen reaction, and an ambient remark.
2. `E:\Felt\docs\ENGINEERING-RULES.md` — the first formal, consolidated set
   of coding rules for the project, built from standing rules that existed
   only scattered across `00-implementer-context.md`/`DELEGATION.md` plus new
   rules written directly from this audit's smell lists.
3. This file — the merged, ranked, de-duplicated cleanup list below.

**Docs only.** No source, config, or test file was changed by WP-38 itself
(the five per-repo audits that feed it were themselves read-only passes, each
already stated as such in its own `ARCHITECTURE.md`).

## Why

Mario's brief: "sort the code since rn is kinda of a blackbox". The 2026-09-24
audit (`AUDIT-2026-09-24.md`) had already found the same god-files
(`brain.py`, `server.py`, `main.gd`, `app.py`) by feel; this WP measures them
properly (line counts, function inventories, import graphs, test coverage)
so the god-file splits in WP-40 have a real spec instead of a vibe, and so
every future WP has a rule book to be checked against instead of relying on
each agent rediscovering the same lessons.

## Where

Repos: felt-core, felt-animation, felt-character-assets, felt-tray,
felt-dashboard, felt-vision, felt-voice, and the umbrella (`E:\Felt` itself —
launcher scripts). New/changed files, all docs:

- `E:\Felt\docs\ARCHITECTURE.md` (new)
- `E:\Felt\docs\ENGINEERING-RULES.md` (new)
- `E:\Felt\docs\plans\impl\WP-38-architecture-audit.md` (new, this file)
- `E:\Felt\docs\plans\impl\README.md` (one row added)
- Pre-existing, read as inputs, unchanged: `E:\Felt\felt-core\ARCHITECTURE.md`,
  `E:\Felt\felt-animation\ARCHITECTURE.md`,
  `E:\Felt\felt-character-assets\ARCHITECTURE.md`,
  `E:\Felt\felt-tray\ARCHITECTURE.md`, `E:\Felt\felt-dashboard\ARCHITECTURE.md`,
  `E:\Felt\docs\architecture\felt-vision.md`,
  `E:\Felt\docs\architecture\felt-voice.md`,
  `E:\Felt\docs\architecture\umbrella-scripts.md`.

## Accept

- [x] `docs/ARCHITECTURE.md` exists, covers all three machines, every
  service's port/launch method, a repo table linking each `ARCHITECTURE.md`,
  config/secrets locations, state locations, and one diagram each for a voice
  reply, a screen reaction, and an ambient remark.
- [x] `docs/ENGINEERING-RULES.md` exists, ≤ 250 lines, numbered/checkable,
  covers structure/config/interfaces/tests/commits/runtime/evidence/
  privacy/error-handling/tooling/agents, each rule with a one-line why.
- [x] This file exists with a ranked, merged, de-duplicated refactor list
  covering all eight source documents, each item tagged repo/what/why/
  effort/risk/agent-ok-or-needs-Claude/target WP.
- [x] The felt-tray `self._hushed` concurrency bug is explicitly flagged as a
  WP-40 must-fix (§ Ranked list, item 3).
- [x] `README.md` has a WP-38 status row placed right after WP-22's row,
  status `🔎 needs review`.
- [ ] Mario has live-reviewed this synthesis (only Mario ticks, per
  `ENGINEERING-RULES.md` rule 27 / `DELEGATION.md`).

## Ranked cleanup list

One merged list, ordered by (impact × how many repos it touches) ÷ effort,
folding duplicate findings across repos into a single row. Effort:
**S**mall / **M**edium / **L**arge. Target WP per the usefulness plan's final
list: **WP-39** = tooling (ruff/pyright/pre-commit/CI), **WP-40** = god-file
splits (felt-animation `server.py`, felt-core `brain.py`, felt-tray `app.py`
— `main.gd` stays with **WP-35**), **WP-42** = dashboard→server-side-app API
move, or a **new small chore** ticket for anything not already covered by a
named WP.

| # | Repo | What | Why | Effort | Risk | Agent | Target WP |
|---|---|---|---|---|---|---|---|
| 1 | felt-animation | Split `server.py` (2095 LOC, 20 routes + ~15 background loops, 15 `global` statements across 14 functions) into routers (presence, playback/reply, props, signals/debug) + a slim `app.py` for lifespan/middleware, with an `AppState` replacing the globals | Biggest single god-file in the whole codebase; centers Mario's "black box" complaint | L | Medium — large surface, full test suite + manual smoke pass required | Needs Claude | WP-40 |
| 2 | felt-core | Split `brain.py` (1080 LOC: routing/privacy dispatch, local vs. cloud replies, two independent + duplicative screen-reaction implementations, a weather-precompute loop, a music-taste loop) into a `brain/` package, re-exported so `api.py`'s imports don't change | Five unrelated responsibilities in one file, confirmed by measurement; matches Track B's own plan | M | Medium — many call sites, `lifespan()` task wiring must keep working; prove against the 359 passing tests | Needs Claude | WP-40 |
| 3 | felt-tray | **Fix the `self._hushed` data race** — written from the status-poll thread (`app.py:191`, no lock) and the `keyboard` callback thread (`app.py:430-439`) with no synchronization; a poll landing right after an unhush can silently overwrite the just-set value | **Flagged as a WP-40 must-fix.** Concurrency bugs don't show up in tests and this one is untested; a silent overwrite means Mario un-hushes her and she stays hushed with no visible cause | S | Medium — subtle concurrency reasoning, needs a careful verification pass (a lock or single-writer redesign) | Needs Claude | WP-40 |
| 4 | felt-character-assets | Split `main.gd` (2868 LOC, 89 functions, no `class_name`/signals) per WP-35's own sketch: extract the clip-library loader + load-time fixes (~370 LOC), the AnimationTree layer controller (~250 LOC), and the procedural pose modifier (~280 LOC) as separate components shared with the planned studio | Same god-file problem as #1/#2, already the exact split WP-35 is designed around — do it there, not twice | L | Medium — frame-ordering guarantees (`mixer_applied`) must survive each move; verify with screenshot + measured gait each time | Needs Claude | WP-35 (not WP-40 — overlaps by design) |
| 5 | felt-tray | Extract a `FeltAnimationClient`, consolidating ~15 ad hoc `httpx` calls scattered across `app.py`/`watcher.py` (no counterpart to the existing `FeltCoreClient`) | Biggest duplication in felt-tray; centralizes mocking, removes copy-paste timeout/error handling | M | Low-medium | agent-ok | new chore |
| 6 | All Python repos (felt-core, felt-animation, felt-tray, felt-vision, felt-voice) | Wire up ruff (lint+format), pyright/basedpyright, pre-commit, and Gitea Actions CI per repo | None of this exists today; every audit found tests passing but nothing enforcing style/types on every push | M | Low | agent-ok (mechanical setup); Claude reviews the CI config once | WP-39 |
| 7 | felt-character-assets | gdlint/gdformat wired into CI, matching the Python repos | Same gap, GDScript side; `main.gd`'s god-file problem is easier to keep from regrowing with a formatter in place | S | Low | agent-ok | WP-39 |
| 8 | felt-dashboard | Move the felt-animation-from-browser calls (`api.ts` — `GET /tone`, `POST /request_started`/`reply_ready`) behind felt-core or a new server-side relay, before Track E's server-hosted app lands | `VITE_FELT_ANIMATION_URL` defaults to `127.0.0.1:8421` — correct for today's felt-tray-hosted desktop window, but unreachable from a phone or a server-rendered session once the app moves server-side (Track E, WP-42) | M (design decision first, then mechanical) | Low once decided | Needs Claude (architecture call) | WP-42 |
| 9 | felt-dashboard | Split `App.tsx` (205 LOC, five inline responsibilities: shell/theme/history/text-send/voice-send) into a `useChat()` hook + a presentational shell | Track E needs Chat/Feed/Daily-briefs/Diary as separate logs; splitting now, with one view, is cheaper than splitting alongside the first new view | S | Low — mechanical extraction | agent-ok | WP-42 |
| 10 | felt-dashboard | Add tests for `App.tsx`'s async flows (history restore, text-chat send + error path, voice-chat send + `playedByAnimation` branching) via Testing Library + a mocked `fetch` | The actual chat logic is currently the least-tested code in either desktop repo relative to its risk (felt-tray's Python equivalent is well covered) | S-M | None — test-only | agent-ok | WP-42 (do before #9's split so the split has a safety net) |
| 11 | felt-core, felt-dashboard | Give `SESSION_ID` one shared source of truth instead of two hand-synced literals (`felt-tray/api_client.py`, `felt-dashboard/App.tsx`) | A typo in either place silently splits chat history into two sessions with no error surfaced | S | Low | agent-ok | new chore |
| 12 | felt-character-assets, felt-animation | Reconcile the three independently hand-synced tag-prefix lists: `main.gd`'s `UPPER_TAG_CLASSES`/`BASE_TAG_PREFIXES`/`FULL_BODY_OVERRIDE_TAGS`, felt-animation's `overlay.py::is_looping_tag`, felt-animation's `gaze.py::DEFAULT_OPT_OUT_TAGS` — at minimum cross-reference in comments, at most have felt-animation derive its rules from the `{"layers"}` report `main.gd` already sends | Three lists, two repos, no shared schema; behavior-determining logic that silently drifts | M | Medium — cross-repo, behavior-determining | Needs Claude | new chore (pairs with WP-40 item 1/4) |
| 13 | felt-animation | Reconcile `cursor.py`/`geometry.py` monitor-span math — have `cursor_fraction_x()` consume `OverlayGeometry`/`monitor_rects()` instead of its own independent `GetSystemMetrics` call | Two sources of truth for "where is the desktop"; surfaces as "come here"/"shoo" misbehaving | M | Medium (the two encode the primary-vs-virtual-desktop distinction slightly differently today) | Needs Claude | WP-40 (bundle with #1) |
| 14 | felt-core | Factor the duplicated OAuth-token-cache pattern (`spotify_client.py`, `google_calendar.py`) into one shared helper | Identical logic duplicated verbatim; a third OAuth integration would copy it again | S | Low, both sites already unit-tested | agent-ok | new chore |
| 15 | felt-core | Extract a shared `try_cloud_then_local()` helper for the five repeated cloud-fallback blocks (`brain.py:242,377,469,559`, `events.py:329`) | Shrinks `brain.py` further, removes copy-paste drift risk | S | Low, well tested | agent-ok (Claude confirms the signature) | WP-40 (bundle with #2) |
| 16 | felt-core | Delete or fix `plugins/change_shirt/` (uses the old `__init__.py`+`manifest.json` convention so it's never loaded, hardcodes `127.0.0.1:8421`, returns a bare `str` instead of `SkillResult`, listed as live in `skills.json`/`tags.json` anyway) | Dead, misleading, would break on load if ever revived; zero test coverage caught none of it | S | None — unreachable | agent-ok (Mario picks delete vs. fix) | new chore |
| 17 | felt-core | Add the missing `.env.example` keys: `FELT_GEMINI_API_KEY` (the actual cloud-enable switch), `FELT_HA_URL`/`_TOKEN`/`_ENTITIES`, `FELT_HP_PRINTER_HOST` | README's rule promises every setting is documented; today a fresh deployer can't discover cloud routing or two integrations exist | S | None | agent-ok | WP-39 |
| 18 | felt-animation | Fix `wardrobe.py`'s three hardcoded absolute paths — move to `Config` (`FELT_WARDROBE_STATE_PATH`, `FELT_TEES_APPROVED_PATH`, `FELT_TEES_DIR`) + `.env.example` entries, add the missing module docstring, move the mid-file import to the top of `server.py` | The one module in felt-animation breaking the project's "no hardcoded paths" rule | S | Low | agent-ok | new chore |
| 19 | felt-animation | Add tests for `wardrobe.py` (`check_and_roll_daily`, the 21-day cooldown in `roll_tee`, `load_wardrobe_state` fallback) — the only source module in the repo with zero coverage | Same file as #18; do together | S | Low | agent-ok | new chore |
| 20 | felt-animation | Rename `%APPDATA%\Felt\props.json` (e.g. `placed_props.json`) to stop colliding with the repo-root prop-definition manifest of the same name | Two unrelated files sharing a filename, different directories — easy to confuse in logs/greps; a stale name means placed props silently don't restore once | S | Low | agent-ok | new chore |
| 21 | felt-tray | Split `capture.py` into `capture_policy.py` (pure, tested) and `capture_win32.py` (ctypes) — the file already documents this intended split in its own header comment | Matches its own stated design; currently both halves live in one file | S | Low | agent-ok | WP-40 (bundle with #3) |
| 22 | felt-tray | Fix `README.md`'s stale "felt-overlay lifecycle" section (describes felt-tray launching the Godot exe via a `src/felt_tray/overlay.py` that **does not exist** — that ownership moved to felt-animation in WP-08) | Exactly the doc-drift behind Mario's "black box" complaint; `ENGINEERING-RULES.md` rule 9 exists because of findings like this one | S | None | agent-ok | new chore |
| 23 | felt-tray | Add `FELT_VISION_URL` to `.env.example` (legacy fallback path, currently hardcoded-default-only) | Undocumented knob for a real, if legacy, fallback path | S | None | agent-ok | WP-39 |
| 24 | felt-tray | Shared poll-loop helper (`interval, tick_fn, stop_event`) for `_status_poll_loop`/`_music_poll_loop` | Two independent hand-rolled loops with no shared helper | S | Low | agent-ok | new chore |
| 25 | felt-tray | Break up `App.__init__` (~68 lines constructing 8 collaborators + ~10 closures) into named `_build_x()` helpers, no behavior change | Readability precursor to #1/#3's larger felt-tray work | S | Low | agent-ok | WP-40 (bundle with #3) |
| 26 | felt-core | Fix `api.py:589` `chat_ws`'s bare `except Exception: await websocket.close()` with a logged exception | The one exception-swallow in the whole codebase with **zero** logging — worst offender across ~50+ broad excepts audited | S | None | agent-ok | new chore |
| 27 | felt-core | Move `router.py`'s 161-line hand-written few-shot prompt out of Python, or split it into one example per skill co-located with that skill | Every new plugin currently also needs a hand-written example maintained in a separate file, contradicting the "drop a folder in, it's a skill" pitch | M (S if just extracted with no behavior change) | Low-medium — routing behavior can shift; verify with `test_router.py` + manual spot-checks | Needs Claude (design call) | new chore |
| 28 | felt-character-assets | Delete confirmed dead code: the unreachable `elif anim_player` branch + `test/*` match block (`main.gd:613-648,2666-2684`, references files confirmed absent from disk), plus `test_view.gd`/`.tscn` (superseded, not wired into `run/main_scene`) | Zero behavior change, shrinks the god file for free; two dead paths, one masking the other | S | None | agent-ok | new chore (bundle with #4) |
| 29 | felt-character-assets | Close two doc gaps: add `view_vsync` to the relay README table (handled but undocumented); mark pre-`CREDITS.md` clips "provenance unknown" explicitly rather than silently absent | Only doc gaps found in an otherwise accurate relay-protocol table; a real gap (license provenance), not just stale prose | S | None | agent-ok | new chore |
| 30 | felt-character-assets | Move `_make_in_place_cycle`/`_symmetrise_cycle` (runtime keyframe surgery on every locomotion clip, on every launch, uncached, identical every time) into an offline step in `AnimToVrmaConverter`'s conversion pipeline | Removes it from the startup hot path entirely; WP-35 already wants to share this code with the studio — bake it into the converter once instead of carrying it in both | L | Medium — touches a sibling repo, needs per-clip re-verification (prove identical output clip by clip) | Needs Claude | new chore (after WP-35 lands) |
| 31 | felt-character-assets | Name the remaining bare tuning literals in `_apply_toon_params` (e.g. `0.15`/`5.0`) and `props.gd`'s ease/duration literals, matching the `BUBBLE_FADE_S`-style siblings already in `main.gd` | Consistency with the file's own better-documented constants | S | None | agent-ok | new chore |
| 32 | felt-vision | Add `.env.example` (document `OLLAMA_URL`, `VISION_MODEL`) and a real README (purpose, setup, dependency on Ollama, the privacy-filtering prompt) | The only repo with **no config file discipline at all** — config is discoverable only by reading `main.py`; README is empty | S | None | agent-ok | WP-39 |
| 33 | felt-vision | Add a `/health` endpoint that validates Ollama reachability, and log on successful startup (today only "starting up" is logged, never readiness) | No way to verify the service is actually ready short of hitting `/analyze` and seeing what happens | M | Low | agent-ok | new chore |
| 34 | felt-voice | Resolve hardcoded *relative* paths (`./models/chatterbox/teto_ref.wav`, `./voices`) to the repo root via `__file__`/`pathlib`, so they don't break if the working directory changes | Only path-hygiene issue found on the Nitro5 side; low risk today only because the systemd unit always sets the right `WorkingDirectory` | S | Low | agent-ok | new chore |
| 35 | felt-voice | Add a `/v1/readiness` endpoint (block until TTS/STT engines are fully warm) and log the RVC-skip reason on startup if `RVC_MODEL_PATH` is unset | No signal today for "fully loaded" vs. "process started"; a silent Piper-only fallback with no logged reason if RVC config is missing | S | Low | agent-ok | new chore |
| 36 | umbrella scripts | Replace `UpdateFelt.ps1`'s blanket `git add -A` + generic commit with explicit paths or an intent-to-add + review step | Already independently called out by `ENGINEERING-RULES.md` rule 18 and `DELEGATION.md` rule 7 — this is the literal script both rules are about | M | Low | agent-ok | new chore |
| 37 | umbrella scripts | Replace name/cmdline-based process killing in `LaunchFelt.ps1`/`UpdateFelt.ps1` with PID files | Fragile — false positives if any other Python script happens to have `felt_animation`/`felt_vision`/`felt_tray` in its command line | M | Low | agent-ok | new chore |
| 38 | umbrella scripts | Add inter-process readiness checks in `LaunchFelt.ps1` (wait for felt-vision's new `/health`, item #33, before starting felt-tray) instead of firing all three in rapid, unordered sequence | If felt-vision is slow to bind, felt-tray's first screen-capture can fail silently | M | Low | agent-ok | new chore (after #33) |
| 39 | umbrella scripts | Log `LaunchFelt.ps1`/`UpdateFelt.ps1`/`StartNitro5.ps1` output to a file (`%TEMP%\LaunchFelt.log` etc.) instead of `Write-Host` only | No way to grep/audit launch history today | S | None | agent-ok | new chore |

### Notes on scope

- Item 4 (`main.gd` splits) is listed for completeness but **targets WP-35**,
  not WP-40 — the usefulness plan is explicit that `main.gd` stays with the
  already-scoped Animation Studio work rather than being split twice.
- Items 6, 7, 17, 23, 32 are grouped as **WP-39** (tooling) even though a few
  are really "add a missing `.env.example` key" — they're bundled there
  because WP-39 is the first WP touching every repo's baseline hygiene, and
  doing them alongside the lint/CI setup avoids a second pass through the
  same files.
- Items 1, 2, 3, 13, 21, 25 are the **WP-40** god-file/concurrency scope
  proper (felt-animation `server.py`, felt-core `brain.py`, felt-tray `app.py`
  + its `self._hushed` race + its documented `capture.py` split).
- Everything tagged **new chore** has no dependency on WP-39/40/35 landing
  first and can be picked up any time by an `agent-ok` session once WP-37's
  board exists to hold it as a ticket.

### Proof

- Files written this WP: `E:\Felt\docs\ARCHITECTURE.md` (new),
  `E:\Felt\docs\ENGINEERING-RULES.md` (new, 237 lines),
  `E:\Felt\docs\plans\impl\WP-38-architecture-audit.md` (new, this file),
  one row added to `E:\Felt\docs\plans\impl\README.md`.
- Inputs read in full (not skimmed): the five per-repo `ARCHITECTURE.md`
  files (felt-core, felt-animation, felt-character-assets, felt-tray,
  felt-dashboard), `docs/architecture/felt-vision.md`, `felt-voice.md`,
  `umbrella-scripts.md`, `00-implementer-context.md`, `DELEGATION.md`,
  `AUDIT-2026-09-24.md` (all 479 lines, including its decisions log),
  `felt-usefulness-plan-2026-09-26.md` (all 527 lines), `POLISH-BACKLOG.md`,
  and the current `README.md` status table.
- Committed together in the same commit as this file — confirm with
  `git log --oneline -1 -- docs/plans/impl/WP-38-architecture-audit.md` in
  `E:\Felt`.
- 39 ranked cleanup items produced, merged from the "Ranked refactor
  suggestions"/"Ranked Suggestions" section of all eight source documents,
  with duplicate findings (e.g. the tag-prefix lists, appearing in both the
  felt-animation and felt-character-assets audits) folded into single rows.

### Not done / unverified

- **No code was touched or tested by WP-38 itself** — this is a synthesis of
  five prior read-only audits, not a new measurement pass. Where a source
  audit's own numbers are cited (LOC counts, test-pass counts), they're
  attributed to that audit's `git ls-files`/`wc -l`/`pytest` run, not re-run
  here.
- **The Gitea board (WP-37) doesn't exist yet**, so none of the 39 items
  above are tickets yet — they become tickets once WP-37 lands, per the
  usefulness plan's own note that WP-38's outputs "become tickets once WP-37
  exists."
- **Mario has not live-reviewed this synthesis.** Per rule 27
  (`ENGINEERING-RULES.md`) and `DELEGATION.md`, status is set to
  `🔎 needs review`, not ticked, and only Mario (or Claude after Mario's live
  review) may change that.
- **`AnimToVrmaConverter` was not audited** by any of the five source
  documents and is absent from the ranked list except as the target of item
  30; it may have its own god-files/smells not captured here.
- **felt-voice was audited from `docs/architecture/felt-voice.md` only** —
  no fresh read of the Nitro5 repo was done for WP-38 itself, since that
  document was already current (2026-09-11/12 dates noted inline) and out of
  reach from this desktop session in the same way the server's felt-core
  vendored copy is.
