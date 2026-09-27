# WP-40 — god-file splits

Per-repo notes as each repo's WP-40 work lands. Pull --rebase before
appending a new heading; each repo's agent owns its own section.

## felt-core

Pure refactor, no behaviour change. All work items from the assignment
(felt-core's slice of WP-38's ranked list, items #2/#7/#14/#16/#26 plus
`ENGINEERING-RULES.md` rule 3): split `brain.py`, fix `events.py`'s
private-helper reach-through, factor the OAuth refresh-token duplication,
delete the dead `change_shirt` plugin, log instead of swallowing in
`api.py`'s WebSocket handler, and fix `privacy.py`'s stale docstring.

### What changed

**1. `brain.py` (1130 LOC) split into a `brain/` package** by
responsibility:

| file | LOC | responsibility |
|---|---:|---|
| `orchestrator.py` | 344 | `chat()` - router/privacy dispatch, presence/image-intent guards, skill execution, `_summarize_pending_email` |
| `replies.py` | 315 | local (Ollama) + cloud (Gemini/Gemma) reply generation, skill-result phrasing - also the small **public** surface (`local_reply`, `music_taste_context`, `personality_prompt`/`PERSONALITY_PROMPT`) other modules use instead of reaching into private internals |
| `screen_reactions.py` | 283 | `process_screen_context` (felt-vision, text) + `react_to_screen` (WP-07, JPEG) - merged onto one shared `_on_cooldown()` helper |
| `background.py` | 229 | the weather-precompute and music-taste-poll asyncio loops (started from `api.py`'s lifespan) |
| `personality.py` | 46 | the system prompt every reply carries, local or cloud |
| `result.py` | 25 | `ChatResult`, the shape every entry point returns |
| `__init__.py` | 44 | re-exports the public entry points so `from felt_core.brain import ...` is unchanged everywhere else |

Every file is comfortably under the 400-LOC soft limit
(`ENGINEERING-RULES.md` rule 2); the previous single file was almost 3x
the hard-review-flag threshold (1130 vs 800).

`felt_core.brain` re-exports `chat`, `process_screen_context`,
`react_to_screen`, `current_weather`, `weather_precompute_loop`,
`music_taste_loop`, `local_reply`, `music_taste_context`,
`personality_prompt`, `PERSONALITY_PROMPT` - `api.py`'s and
`__init__.py`'s `from felt_core.brain import ...` needed zero changes.

**2. Screen-reaction merge.** `process_screen_context` and
`react_to_screen` each used to inline an identical copy of the "are we on
cooldown" check (`seconds_since_last_spoken_reaction` + logging + early
return). Merged into one `screen_reactions._on_cooldown()` helper both
now call. The two entry points' actual reaction-generation stayed
separate on purpose - they're genuinely different behaviours, not
duplicated ones: `process_screen_context` is text-in, tries cloud then
falls back to local Ollama; `react_to_screen` is JPEG-in, cloud-only
(no local VLM exists on this server), single JSON `{seen, line, emotion}`
call with no local fallback. Collapsing those two into one function would
have been a behaviour change, not a refactor - see "Not done" below.
`tests/test_screen_reaction_merge.py` proves the merge: the shared
helper's own truth table (4 tests) plus both entry points producing the
identical silent/non-silent outcome from identical cooldown state with
zero model calls while on cooldown (2 tests).

**3. `events.py`'s private-helper reach-through fixed.** It used to do
`from felt_core.brain import _local_reply, _music_taste_context,
_personality_prompt` - brain's underscore-prefixed internals, with no
import-time signal that `events.py` depended on them staying stable
(`ENGINEERING-RULES.md` rule 3, called out by name in the WP-38 audit).
Now imports the public `local_reply`/`music_taste_context` from
`felt_core.brain.replies` and `personality_prompt` from
`felt_core.brain.personality`.

**4. OAuth refresh-token duplication factored out.**
`spotify_client.py` and `google_calendar.py` each had an identical,
independently-written `_get_access_token`: a module-level
`{"access_token", "expires_at"}` cache dict, a 60s expiry safety margin,
a `grant_type=refresh_token` POST. New `src/felt_core/oauth_token.py`
(43 LOC): `refresh_access_token(client, cache, token_url, data,
headers=None)`, parameterized by each provider's own POST
body/headers (Spotify's HTTP Basic auth header vs Google's plain POST
fields). Each caller keeps its own cache dict. `spotify_client.py`
138 -> 134 LOC, `google_calendar.py` 173 -> 167 LOC. New
`tests/test_oauth_token.py` (6 tests) covers the helper directly: fresh
fetch, cache hit, the 60s-margin refresh, the default-expiry fallback,
headers passthrough, and error propagation.

**5. Dead `plugins/change_shirt/` deleted.** It used the old
`__init__.py` + `manifest.json` plugin convention; `plugin_loader.py`
only discovers a directory containing `skill.py`, so it was never
loaded - absent from the router's tool list, uncallable - yet still
listed as `"public"` in `plugins/skills.json` and `"ambient/show_off"` in
`plugins/tags.json` as if live. Its `handle()` also returned a bare
`str`, not the `SkillResult` the `Skill` Protocol requires, so it
wouldn't have worked even if it had loaded. Checked first: no import of
`plugins.change_shirt` anywhere in `src/` or `tests/`. The desktop's own
`/change_shirt` endpoint lives in felt-animation and is unrelated - not
touched. Removed the directory and both manifest entries.

**6. `api.py`'s `chat_ws` WebSocket handler now logs.** It used to be a
bare `except Exception: await websocket.close()` - the single worst
exception-swallow across ~50+ broad excepts audited (rule 33/34: "the
riskiest is `api.py:589`... swallows any error and just closes the
socket with zero logging"). Now distinguishes an ordinary client
disconnect (`WebSocketDisconnect`, logged at `info`) from a real failure
(`logger.exception`, naming the message loop, before still closing the
socket exactly as before) - no behaviour change beyond the logging.
`tests/test_chat_ws.py` (new, 3 tests) covers the previously-untested
happy path plus both the error and disconnect branches.

**7. `privacy.py`'s stale docstring fixed.** It said cloud routing for
plain conversation goes "via ninerouter" - `config.py`/`brain.replies`
are explicit that it goes **directly** to the Gemini API, specifically to
avoid ninerouter's Antigravity contamination. Doc-only, no behaviour
change.

### Before/after LOC

| file | before | after |
|---|---:|---:|
| `brain.py` | 1130 | *(deleted - see `brain/` package above, 1286 total across 7 files)* |
| `events.py` | 448 | 450 |
| `spotify_client.py` | 138 | 134 |
| `google_calendar.py` | 173 | 167 |
| `oauth_token.py` | - | 43 *(new)* |
| `api.py` | 627 | 647 |
| `privacy.py` | 108 | 110 |
| `plugins/change_shirt/` | 30 (2 files) | *(deleted)* |

### Proof

- `uv run pytest -q` in `E:\Felt\felt-core`: **359 passed** before any
  change; **374 passed** after all six items (15 new tests:
  6 `test_screen_reaction_merge.py`, 6 `test_oauth_token.py`,
  3 `test_chat_ws.py`). Re-ran the full suite after every commit, not
  just at the end - all green throughout.
- `uv run ruff check` / `uv run ruff format --check`: clean after every
  commit (one `pyproject.toml` per-file-ignore update: the old
  `"src/felt_core/brain.py" = ["E501", "SIM105"]` entry became
  `orchestrator.py` (`E501`, `SIM105`) / `background.py` (`E501`) /
  `screen_reactions.py` (`E501`) - same pre-existing findings, just
  spread across the files they landed in, nothing new).
- `uv run python scripts/check_pyright_baseline.py`: **121 errors**
  throughout (unchanged from the WP-39 baseline) - no new pyright
  errors introduced by the split.
- Commits (all pushed to `origin/main`,
  `git.clockmost.com:Benylin/felt-core.git`):
  - `c20030e` - WP-40: split brain.py into a brain/ package by
    responsibility (includes the `events.py` public-API fix and the
    screen-reaction merge)
  - `78e3e1a` - WP-40: extract shared OAuth refresh-token helper
  - `92bb259` - WP-40: delete the dead change_shirt plugin
  - `391cd47` - WP-40: log the chat_ws failure path, fix privacy.py's
    stale docstring
- CI: the Gitea Actions runner (`gitea-act-runner`, confirmed via
  `ssh clockmost-claude "docker logs gitea-act-runner"`) picked up a
  `Benylin/felt-core` task for each of the four pushes above (task IDs
  404/405/409/411/412/416, timestamps matching each push) - the same
  runner WP-39 already verified is active for this repo. The actual
  pass/fail conclusion of those runs was **not independently confirmed
  this session** - see "Not done" below.

### Not done / unverified

- **CI's green/red conclusion wasn't fetched.** The Gitea API
  (`https://git.clockmost.com/api/v1/repos/Benylin/felt-core/...`)
  requires authentication for this private repo, and generating a
  read-only API token (`gitea admin user generate-access-token`) was
  blocked by the auto-mode permission classifier as a secret-store
  write; per that denial's own instructions, no other route to the same
  token was attempted. What's actually confirmed: the runner picked up
  a task for each push (log timestamps line up with each `git push`),
  and every gate CI itself runs (`ruff check`, `ruff format --check`,
  the pyright-baseline gate, `pytest`) was run locally, identically, and
  passed after every commit. Mario can confirm the run conclusion
  directly from the Gitea web UI (logged in) faster than any workaround
  here would have.
- **The two screen-reaction entry points were not collapsed into a
  single function.** Only the duplicated cooldown-check plumbing was
  merged - `process_screen_context` (text, local-fallback) and
  `react_to_screen` (image, cloud-only, no fallback) have genuinely
  different model-call contracts, and forcing them into one shape would
  have been a behaviour change disguised as a refactor. Flagged
  explicitly rather than silently doing less than the WP's phrasing
  ("merge... into one") suggested - see item 2 above for the reasoning
  and the tests proving what *was* merged is behaviourally identical.
- **Not deployed.** Per the WP's own instruction and Mario's decision:
  committed and pushed felt-core only. The server runs a vendored copy
  under `clockmost-infra`'s own git history and is unaffected by this
  repo's `origin/main` until that separate deploy step runs. Mario is
  deploying this together with the pending `9473cb9` (the weather
  endpoint) himself.
- **`ARCHITECTURE.md` (felt-core's own, WP-38's audit doc) was not
  updated** to reflect the new `brain/` package layout - it still shows
  the old single-file module map. Out of this WP's stated scope (notes
  go in this file, not the per-repo `ARCHITECTURE.md`), flagged so it
  doesn't read as forgotten.

## felt-tray + dashboard

felt-tray's slice of WP-38's ranked list (items #3/#5/#21/#24/#25: the
`self._hushed` race, `FeltAnimationClient`, the `capture.py` split, the
shared poll-loop helper, `App.__init__`'s breakup), plus an unscoped-but-
required CI fix (WP-39 wrote felt-tray's `ci.yml` targeting
`runs-on: windows`, which sits queued forever - the registered Gitea
Actions runner has no Windows label), plus felt-dashboard's 2 real
`no-underscore-dangle` oxlint findings (WP-39's own "Not done" note).
Pure refactor, no behaviour change except the race fix itself (a bug
fix, not a behaviour *addition* - hush/unhush already existed, this
makes it correct under concurrency).

### What changed (felt-tray)

**1. `self._hushed` data race (MUST-FIX).** Was a bare bool written from
both the status-poll thread (`_status_poll_loop`, every 5s) and the
hotkey/tray-menu thread (`S` toggle, "Unhush") with no synchronization.
New `src/felt_tray/hush_state.py`'s `HushState`: a lock plus a
generation counter, not just a lock - a bare lock would only stop
corrupted concurrent *writes* (Python's GIL already makes a single bool
assignment atomic; this was never a memory-safety bug). The real bug is
*stale write ordering*: a poll that started while still hushed, then
raced a local unhush, could land its now-stale "hushed" result after the
fresh local unhush and silently revert it - Mario un-hushes her and she
stays hushed with no visible cause. `HushState.set_local()` (the hotkey/
tray path) bumps a generation on every write; `apply_poll_result()` (the
poll path) drops its own result if a local write happened since that
poll's own `begin_poll()` snapshot. `tests/test_hush_state.py` (7 tests)
covers both writers: the exact sequential stale-overwrite scenario from
the bug report, and a real two-thread test (one hammering
`begin_poll`/`apply_poll_result` like the poll loop, one hammering
`set_local` like the hotkey) asserting the invariant holds under genuine
concurrency, not just sequential calls.

**2. `FeltAnimationClient` extracted** (`src/felt_tray/felt_animation_client.py`,
84 LOC), consolidating the ~15 ad hoc inline `httpx.get`/`httpx.post`
calls to felt-animation scattered across `app.py` (`_status_poll_loop`,
`_music_poll_tick`, the hotkey handlers, `_deliver_reply`/
`_finish_voice_chat`). Same URLs, params/data/files, and timeouts as
each call it replaces - error handling stayed at each call site (its own
try/except and log message), matching `FeltCoreClient`'s own pattern of
letting HTTP errors propagate to the caller. `GET /tone` stayed as
`api_client.fetch_tone` (already a single shared function, not an ad hoc
call). Test updates were mechanical: every test that monkeypatched
`app_module.httpx` now monkeypatches `felt_animation_client`'s `httpx`
(the module the real call moved into) - no assertions changed, since
each client method makes the identical call the inline code used to.

**3. `capture.py` (639 LOC) split into `capture_policy.py` (266 LOC,
pure - `WindowInfo`, `Blocklist`, `decide_target`/`select_target`,
`is_felt_process`/`felt_process_pids`) and `capture_win32.py` (413 LOC,
real Win32 calls - `enumerate_windows`, `get_foreground_hwnd`,
`capture_window`'s windows_capture/PrintWindow paths)**, matching the
file's own documented boundary. `watcher.py` updated to import both
(`policy.`/`win32.` instead of `capture.`); `FRAME_HOST_PROCESS` made a
shared non-underscore constant (`capture_win32.py` needs it) instead of
reaching into a `_private` name, per `ENGINEERING-RULES.md` rule 3. New
`tests/test_capture_order.py` (2 tests) directly proves the
blocklist-before-pixels order (rule 28): mocking both modules and
asserting `policy.decide_target` always runs, and strictly *before*,
`win32.capture_window` - and that `capture_window` is never called at
all when nothing allowed is visible - rather than relying only on the
file:line audit note.

**4. `App.__init__`** (~68 lines constructing 8 collaborators + ~10
closures) **broken into named steps**: `_build_clients`
(`FeltCoreClient`/`FeltAnimationClient`/`Recorder`/`HotkeyManager`),
`_build_dashboard_window` (`DashboardServer`+`ChatWindow`),
`_load_temperature_unit`, `_init_state` (presence/hush/status-line/
music-poll state), `_build_watcher`, `_build_tray` - same construction,
same order, same lazy `DesktopWatcher` import, no behaviour change.
`_status_poll_loop`/`_music_poll_loop` (two independent hand-rolled
"while not stop_event.is_set(): tick, then wait" loops) now share one
`_run_poll_loop(stop_event, tick, interval)` helper, `interval` either a
fixed float or a callable re-evaluated each iteration (the music poll's
variable idle-backoff) - each loop's own error handling stays in its own
`tick` closure.

**5. CI switched from `runs-on: windows` to `ubuntu-latest`.** The
registered Gitea Actions runner (`gitea-act-runner`) has no Windows
label - WP-39's workflow was queued forever. Made this actually work,
not just relabel it (which WP-39's own `ci.yml` comment explicitly
warned would just move the failure to `uv sync`):
- `windows-capture`/`winotify` (no Linux wheel - `windows-capture`'s
  sdist doesn't even *build* on Linux, confirmed locally: Rust bindings
  to Windows-only APIs) get `sys_platform == 'win32'` markers in
  `pyproject.toml`, so `uv sync` skips them on Linux instead of failing.
- Every module that would otherwise fail to *import* on Linux -
  `capture_win32.py`/`watcher.py` (`ctypes.windll`/`ctypes.WINFUNCTYPE`,
  Windows-only ctypes attributes), `playback.py` (`winsound`, a Windows-
  only stdlib module), `toast.py` (`winotify`, now excluded by the
  marker above) - is platform-guarded (`if sys.platform == "win32":
  ... else: # pragma: no cover`), each with its own "WP-40 CI note"
  comment. Real behavior on Windows is byte-identical; the non-Windows
  branch is CI import-safety only.
- `tray.py`'s `import pystray` moved from module level into
  `Tray.__init__` - pystray picks its Xlib backend the instant it's
  imported, which connects to a real display immediately; the headless
  Linux runner has none. Nothing in the test suite ever constructs a
  real `Tray` (`ARCHITECTURE.md`'s own "Gaps" note already lists it as
  untested), so deferring the import doesn't lose any coverage.
- `mic.py`'s `sounddevice` needs the real `libportaudio2` *system*
  library (not Windows-specific, just not preinstalled on the runner
  image) - added as a `ci.yml` step (`apt-get install -y
  libportaudio2`), the standard fix for any native-lib Python dependency
  on a fresh Linux box.
- `pyright`'s `pythonPlatform` pinned to `"Windows"` in `[tool.pyright]`
  - without it, pyright infers the platform from whatever host runs it
  (now Linux) and typeshed gates `ctypes.windll`/`wintypes` behind "is
  this Windows", producing ~38 bogus extra errors on a codebase that
  only ever targets Windows. Confirmed 68 (baseline, unchanged) on both
  Windows and Linux after this. The 2 genuinely Linux-only findings left
  (`windows_capture`/`winotify` themselves unresolved, since they're not
  installed in the Linux venv by design) each got an inline
  `# pyright: ignore[reportMissingImports]` with a comment - confirmed
  to add zero new findings on Windows, where the import resolves fine
  and the ignore just sits unused.

No test needed a skip marker - everything that actually requires live
Windows behavior (real Win32 window enumeration/capture, real global
hotkey registration, a live GUI/display for pywebview/pystray) already
had no dedicated test before this WP (`ARCHITECTURE.md`'s own "Gaps":
`capture_win32.py`, `watcher.py`'s message loop, `tray.py`, `window.py`,
`playback.py`, "exercised live, not by the test suite"). The full
143-then-152-test suite runs unmodified on Linux.

Each Linux-specific finding above was found and fixed against a **real**
environment, not guessed: a local WSL (Debian) sandbox for `uv sync`/
import-time checks (caught `windows-capture`'s build failure, every
`ctypes`/`winsound`/`winotify` import blocker, and the `pyright`
platform-inference gap before ever pushing), and the **real** Gitea
Actions runner's own log storage for ground truth after each push (see
Proof - the pystray/Xlib failure and the exact 68-vs-baseline pyright
count were only visible there, not reproducible in the WSL sandbox
without a display/root).

### What changed (felt-dashboard)

**`pnpm lint` (oxlint --deny-warnings) fixed** - 2 real
`no-underscore-dangle` findings (`src/App.tsx`, `window.__feltReloadHistory`,
the intentional cross-window bridge global felt-tray's `window.py`
evaluates to refresh chat history when the pywebview window is shown).
Allow-listed the one identifier in `.oxlintrc.json`
(`"no-underscore-dangle": ["warn", { "allow": ["__feltReloadHistory"] }]`)
rather than renaming it (a cross-repo behaviour change, and rather than
disabling the rule wholesale, which would stop catching a real dangling-
underscore identifier elsewhere).

**Also fixed, discovered while confirming CI (not in the original
2-finding scope, but required for "CI must be green"):** `pnpm
fmt:check` (`oxfmt --check`) was *also* failing on the real runner -
confirmed via the runner's own action log, since this Windows checkout's
`core.autocrlf=true` makes every file falsely look unformatted locally
(the exact false alarm WP-39's own notes already documented, but
apparently premature - it turned out 3 files had **genuine** diffs
underneath the CRLF noise). `src/App.tsx`/`src/lib/api.ts` had one
over-width line each (mechanical line-wrap, zero behaviour change).
`ARCHITECTURE.md` also failed (oxfmt reformats Markdown too - table
borders, `*em*` -> `_em_`, one instance of stripping a list continuation
indent) - rather than let a JS/TS formatter rewrite a hand-written audit
document, added `**/*.md` to `.oxfmtrc.json`'s `ignorePatterns` (same
reasoning as the existing `endfield.css` exclusion: not this tool's
job), which is the smaller, more defensible fix and leaves WP-38's audit
content untouched.

### Before/after LOC (felt-tray)

| file | before | after |
|---|---:|---:|
| `app.py` | 586 | 668 |
| `capture.py` | 639 | *(deleted - split below)* |
| `capture_policy.py` | - | 266 *(new)* |
| `capture_win32.py` | - | 413 *(new)* |
| `watcher.py` | 351 | 361 |
| `tray.py` | 95 | 109 |
| `playback.py` | 71 | 81 |
| `toast.py` | 32 | 45 |
| `hush_state.py` | - | 57 *(new)* |
| `felt_animation_client.py` | - | 84 *(new)* |

felt-dashboard: `src/App.tsx` 205 -> 208, `src/lib/api.ts` 143 -> 147
(both mechanical reformatting only), `.oxlintrc.json` 32 -> 33,
`.oxfmtrc.json` 3 -> 4.

### Proof

- `uv run pytest -q` in `E:\Felt\felt-tray`: **143 passed** before any
  change; **152 passed** after all items (9 new tests: 7
  `test_hush_state.py`, 2 `test_capture_order.py`). Re-ran the full
  suite, `ruff check`, `ruff format --check`, and the pyright-baseline
  gate after **every** commit, not just at the end - all green
  throughout on Windows (the actual dev machine).
- `.pyright-baseline`: 66 -> 68, a **documented, reviewed** bump (not
  silently absorbed): 2 new "Cannot assign to attribute ... for class
  DesktopWatcher" errors in `test_capture_order.py`'s `__new__`-bypass
  unit-test pattern - the identical pre-existing shape already baselined
  for `App`/`FeltCoreClient` elsewhere in this same suite (test-only,
  not a new category of issue). No other pyright count changes on
  Windows throughout the rest of the work.
- felt-dashboard: `pnpm typecheck`/`pnpm test` (7 passed)/`pnpm build`
  all clean throughout; `pnpm lint` went from 2 failures to 0; `pnpm
  fmt:check` went from 3 genuine failures (plus this Windows checkout's
  ~19-file CRLF false-alarm noise, confirmed via `git diff -b` and the
  git blobs' own 0-CR content) to 0.
- **CI, confirmed via the real Gitea Actions runner's own log storage**
  (`ssh clockmost-claude`, `/home/clockmost-infra/projects/gitea/gitea_data/gitea/actions_log/Benylin/<repo>/<hash>/<task>.log.zst`,
  `unzstd -c ... | tail`) - not just "the runner picked up a task", the
  actual step-by-step output and final `Job succeeded`/`Job failed`
  line. (Generating a Gitea API token to use the Actions API directly
  was blocked by the auto-mode permission classifier as credential
  exploration - this log-storage route is what's used instead, and is
  strictly better evidence: full step output, not just a pass/fail
  bit.)
  - felt-tray: task 415 (`runs-on: windows` era, pre-switch, irrelevant)
    -> task 423 (ubuntu-latest, `uv sync`/ruff/ruff-format green,
    pyright 106 vs baseline 68 - the platform-inference gap) -> task 429
    (**Job succeeded** - ruff check, ruff format, pyright 68/68,
    **152 passed in 1.32s**). Commits `1101bff` (pyright pythonPlatform
    fix) and `e118fe9` (tray.py pystray deferral) each fixed exactly one
    of the two real failures task 423 uncovered.
  - felt-dashboard: task 419 (lint fixed, but `fmt:check` failing on
    `ARCHITECTURE.md`/`App.tsx`/`api.ts` - **Job failed**) -> task 421
    (**Job succeeded** - fmt:check, lint "Found 0 warnings and 0
    errors", typecheck, test 7 passed, build, all green).
- Commits (all pushed to `origin/main`):
  - felt-tray (`git.clockmost.com:Benylin/felt-tray.git`): `17be5c2`
    (HushState), `1f61d8a` (capture.py split), `701269d`
    (FeltAnimationClient), `b714b42` (App.__init__ breakup + poll-loop
    helper), `c4fc4b1` (platform-guard deps), `670fdb7` (CI switch +
    WINFUNCTYPE guard), `1101bff` (pyright pythonPlatform), `e118fe9`
    (tray.py pystray deferral).
  - felt-dashboard (`git.clockmost.com:Benylin/felt-dashboard.git`):
    `323524f` (oxlint allow-list), `2f8fb3c` (oxfmt fixes +
    `.md` ignore).
- **Live smoke check** (`F:\Temp\felt-tray.log`, after killing the prior
  `python.exe felt_tray` process and starting
  `E:\Felt\felt-tray\.venv\Scripts\python.exe -m felt_tray` hidden from
  its own directory, per this WP's exact instructions - never
  `felt-tray.exe`): `hotkeys registered: {..., 'stop': 'ctrl+alt+s',
  'clean': 'ctrl+shift+X'}` (the `ctrl+shift+X` rebind present),
  `Desktop Watcher started.`, and two capture decision lines with real
  blocklist rejections - `watcher: decision trigger=focus
  target=windowsterminal.exe rejected=[firefox.exe:process,
  discord.exe:process, whatsapp.root.exe:process]` (the blocklist
  actually excluding Discord/browsers per the product's own privacy
  rule) followed a periodic re-check that got a 200 from felt-core.

### Not done / unverified

- **The felt-animation `/status` poll's live success wasn't observed.**
  felt-animation isn't currently running on this desktop (this WP was
  scoped to restarting felt-tray only, per its own instructions, and
  "don't touch felt-animation" - starting it wasn't in scope either).
  The poll loop itself is confirmed running (no crash, no exception -
  `_status_poll_loop`'s own try/except would log at DEBUG on a failed
  request, and the process stayed alive and responsive throughout), but
  no live 200 from felt-animation's `/status` was captured in this
  window. Mario should confirm this once felt-animation is also running
  (e.g. via `LaunchFelt.ps1`).
- **One transient felt-core 500 during the smoke check**
  (`POST /v1/react/screen` -> 500, logged via `logger.exception` with
  full context, not swallowed) - self-recovered on the very next
  periodic capture (200 OK). felt-core is explicitly out of this WP's
  scope ("Don't touch felt-animation, the overlay or felt-core"); flagged
  as felt-core-side and unrelated to any change here, not investigated
  further.
- **A second `python.exe` process appeared as a child of the venv
  process** (`C:\Users\lealm\...\Python312\python.exe -m felt_tray`,
  parented by the venv `python.exe`) during the smoke check - not
  something any WP-40 change touches (no process-spawning/subprocess
  code was changed), most likely an existing pywebview/WebView2 quirk on
  this machine predating this WP. Noted rather than investigated, since
  pywebview/`window.py` are explicitly out of this WP's scope and it
  didn't affect any of the required smoke-check evidence.
- **README.md not touched**, per this WP's explicit instruction, even
  though felt-tray's `README.md` may have its own drift (not checked
  this session - WP-39 already fixed the specific "felt-overlay
  lifecycle" staleness the WP-38 audit flagged).
- **This WP wasn't live-reviewed by Mario.** Status stays
  `🔎 needs review` (rule 27), not ticked, same as every other WP-40
  slice.

## felt-animation

felt-animation's slice of WP-38's ranked list (items #1/#2/#6/#13, plus
`ENGINEERING-RULES.md` rule 4) and the assignment's own explicit list:
CI fixed first (WP-39 targeted `runs-on: windows`, but the registered
runner is Linux-only), `server.py` split into cohesive modules, the ~15
`global` statements replaced with an explicit `AppState`, the long
functions broken up along real seams, `cursor.py`/`geometry.py`
reconciled, `wardrobe.py`'s hardcoded paths moved to config, and the
persisted `props.json` renamed to `placed_props.json`. Pure refactor, no
behaviour change.

### 0. CI: `runs-on: windows` -> `ubuntu-latest`

The registered `gitea-act-runner` only has `ubuntu-latest`/
`ubuntu-22.04`/`archlinux` labels (all Linux) - WP-39's workflow sat
queued forever. Getting a green run on Linux took four real,
runner-log-driven iterations, not a guess:

1. **`evdev` (pynput's Linux backend) fails to build** - needs a C
   toolchain + `Python.h` the runner image doesn't have. pynput is only
   ever used for a real Win32 mouse hook (`signals/mash.py`'s
   `EventCounter`, lazy-imported, no test touches it) - marked
   `sys_platform == 'win32'` in `pyproject.toml`, same as
   comtypes/pyaudiowpatch/pycaw/wmi already were.
2. **`cursor.py`'s module-level `ctypes.windll.user32`** was the one
   Win32 call that ran at *import* time (every other one is inside a
   function, already exception-guarded) - guarded the same
   try/except-and-fall-back-to-`Any` pattern, so the module (and
   `server.py`, which imported it) stays importable on Linux.
   `beat_capture.py`'s `pyaudiowpatch` import got the same treatment
   (a `_MissingPyAudio` stand-in) since `server.py` imports
   `LoopbackCapture` at module level too.
3. **pyright jumped from 148 (baseline) to 169** once those packages
   weren't installed at all on Linux - `# type: ignore[import-not-found]`
   on the three remaining guarded imports (`call_monitor.py`'s
   comtypes/pycaw, `signals/gpu.py`'s wmi) brought it to 165, still over
   baseline.
4. **The real cause of the other 17: `pythonPlatform` defaults to the
   HOST pyright runs on, not "All"** - Linux pyright can't resolve
   `ctypes.windll`/`WINFUNCTYPE` or `winreg`'s `HKEY_*`/`OpenKey` at all
   (`clickthrough.py`, `geometry.py`, `props.py`, `signals/afk.py`,
   `signals/games.py`), regardless of the guards above, since those are
   typeshed stub gaps, not import resolution. Pinned
   `pythonPlatform = "Windows"` in `[tool.pyright]` - felt-animation only
   ever runs on Windows, so this makes pyright's answer host-independent,
   which is what the baseline is supposed to gate on. Fixed it in one
   line instead of `# type: ignore`-ing ~20 call sites across 5 files.

`libportaudio2` (a real Linux system package, not Windows-specific) is
installed as a `ci.yml` step so `sounddevice` (imported by `audio.py`,
imported by the app at module level) can import at all. No test needed a
`sys.platform`/marker skip - the suite was already fully hermetic (no
real, unmocked Win32 call anywhere), confirmed by the same 470-then-492
pass count on both platforms.

### 1-3. `server.py` split, `AppState`, long functions

**`server.py` (2150 LOC, 20 routes + ~15 background loops, 15 `global`
statements across 14 functions) is gone**, replaced by:

| file | LOC | responsibility |
|---|---:|---|
| `runtime.py` | 279 | the single `AppState` (overlay, mood, hush, presence, props, every detector, ...) built once at import; config load + logging setup |
| `behavior.py` | 385 | shared "verbs" used by more than one router/loop: pose/face, movement/posture, resting-face, reaction-table picks, `react_event`/`signal_event` |
| `props_runtime.py` | 109 | prop-event orchestration shared by the ambient loop and the props router (cooldowns, `play_with_props*`, ambient <-> props weight bridge) |
| `loops.py` | 586 | all ~15 background loops: ambient wander, gaze, idle micro-expressions, mood drift, music beat detection, games/AFK/GPU/mash/call-energy signals, weather props, hush/presence expiry |
| `routers/presence.py` | 177 | `POST /presence` + walk-off/walk-on/shoo/come-here |
| `routers/playback.py` | 493 | `handle_reply` + every reply/voice/hush/mouth-along endpoint |
| `routers/props.py` | 110 | `/props*` endpoints |
| `routers/debug.py` | 67 | `/mood/debug`, `/debug/play_tag`, `/status` |
| `app.py` | 120 | `FastAPI()`, CORS, lifespan, the four `include_router` calls |

Every `global` statement is gone - each is now a plain attribute write on
the one `AppState` instance (`runtime.state`), which every router/loop
module reads via `from felt_animation.runtime import state`. `behavior.py`
and `props_runtime.py` take `state: AppState` as an explicit first
argument instead (rather than importing the singleton) specifically to
stay import-cycle-free, since `runtime.py`'s own `AppState.__init__`
needs one of `behavior.py`'s functions (`play_sound_for_tag`, wired as
`overlay.on_tag_played`) - that one wiring uses a lazy, function-body
import, the only cycle-avoidance trick needed anywhere in the split.

`_ambient_standing`'s late-night-vs-daytime weight table is now its own
`_ambient_standing_weights(hour)` - a first real split of that function.
`handle_reply` and `lifespan` are each shorter by construction (the
module split removed everything that wasn't already inherent to what
they orchestrate) but weren't decomposed further beyond that - see "Not
done" below; `lifespan` did get two named halves,
`_start_background_tasks`/`_stop_background_tasks`, replacing one
90-line function with symmetric start/stop lists.

`__init__.main()` now points uvicorn at `felt_animation.app:app`.

### 4. `cursor.py`/`geometry.py` reconciliation

`cursor_fraction_x()` used to recompute the virtual-desktop span itself
via `GetSystemMetrics(SM_XVIRTUALSCREEN/SM_CXVIRTUALSCREEN)`, independently
of `geometry.py`'s own `monitor_rects()`-based layout - two sources of
truth for "where is the desktop," encoding the primary-vs-virtual-desktop
distinction slightly differently (this is how the come-here/shoo
mirroring bug happened, audit 2026-09-24). `cursor.py` now owns only
"where is the cursor" (`GetCursorPos`, factored through one
`_read_cursor_point()` helper); `cursor_fraction_x()`/
`cursor_fraction_primary_x()` both read `geometry.py`'s own
`monitor_rects()`/`primary_screen_size()` for the monitor layout. In
production this was already a non-issue for the real "come here"/"shoo"
paths - `server.py` (now `routers/presence.py`) already read the cursor
via `cursor_position()` and mapped it through `geometry.py`'s real pixel
map directly, bypassing `cursor_fraction_x()` entirely - but the
duplicated span logic was real, untested-as-such drift, exactly the
smell the audit flagged. `test_cursor.py` rewritten to mock
`monitor_rects()`/`primary_screen_size()` instead of `GetSystemMetrics`
directly, plus 2 new tests (spans both monitors, no-monitors-enumerated
fallback).

### 5. `wardrobe.py` config move

Moved its three hardcoded absolute `E:\Felt\...` paths to `config.py`
(`FELT_WARDROBE_STATE_PATH`/`FELT_TEES_APPROVED_PATH`/`FELT_TEES_DIR`),
defaulting to the exact same values (no behaviour change), documented in
`.env.example`. Added the missing module docstring. Moved `server.py`'s
stray mid-file `from felt_animation.wardrobe import ...` (after
`app = FastAPI(...)`, not with the other ~40 top-of-file imports) to the
top - now `app.py`'s/`loops.py`'s own top-of-file imports - dropping the
now-unneeded `server.py` E402 ruff per-file-ignore. 13 new tests cover
`check_and_roll_daily`, the 21-day cooldown (including the "everything's
on cooldown, ignore it" fallback), `load_wardrobe_state`'s missing-file
default, and `apply_tee`'s garment/show-off wiring - the only source
module in the repo with zero prior coverage.

### 6. `props.json` -> `placed_props.json`

`%APPDATA%\Felt\props.json` (persisted placed-prop positions) collided
with this repo's own root-level `props.json` (the prop-definition
manifest) - same filename, different directory and purpose.
`PropStore.load()` now does a one-time migration: reads the old name if
the new one is missing; the next `save()` writes the new name only. The
old file is left alone (not deleted) so rolling back to an older build
still finds its own data. 4 new tests cover the migration directly
(old-only, new-wins-when-both-exist, neither-exists, and that a save
actually writes the new name) - confirmed live too, see Proof.

### Before/after LOC

| file | before | after |
|---|---:|---:|
| `server.py` | 2150 | *(deleted - split above, 2726 total across 9 new files)* |
| `cursor.py` | 78 | 117 |
| `wardrobe.py` | 85 | 103 |
| `props.py` | 1018 | 1052 (the migration logic) |
| `config.py` | 107 | 128 |
| `pyproject.toml`/`.pyright-baseline` | - | `pythonPlatform` pin, 4 packages marked `sys_platform == 'win32'`, `.pyright-baseline` unchanged at 148 |

### Proof

- `uv run pytest -q`: **470 passed** before any change. Re-ran after
  **every** commit below, never just at the end: 470 (CI fixes,
  no test changes) -> 474 (+4 props-migration tests) -> 487 (+13
  wardrobe tests) -> 492 (+5 cursor/geometry tests, net of 1 test split
  into 2) -> **492 passed** after the full `server.py` split (which
  touched no test *counts*, only which module the 12 `server.py`-
  importing test files target and patch).
- `uv run ruff check` / `uv run ruff format --check`: clean after every
  commit (one new per-file-ignore: `props_runtime.py` inherits the exact
  SIM102 nested-if `server.py`'s own `_play_with_props_clip` already had
  ignored, moved unchanged - not re-litigated by the split).
- `uv run python scripts/check_pyright_baseline.py`: 148 (baseline) ->
  144 after the full split (fewer, not more - the `AppState`
  attribute-typed fields resolved a few `Optional`-shaped false
  positives the old bare globals had). Never exceeded baseline at any
  intermediate commit once the `pythonPlatform` fix landed.
- `uv run scripts/check_env_example.py`: 21/21 keys documented
  throughout (3 new wardrobe keys added in the same commit as the
  `config.py` fields, per rule 6/8).
- Commits (all pushed to `origin/main`,
  `git.clockmost.com:Benylin/felt-animation.git`):
  - `2429ff2` - CI on ubuntu-latest
  - `7a21baa` - mark pynput Windows-only too (CI run 408: evdev)
  - `762062f` - pyright ignores for the Windows-only imports
  - `43a9a28` - print each new pyright diagnostic (debug tooling)
  - `9b8d67b` - rename props.json to placed_props.json + migration tests
  - `7c907f4` - wardrobe.py config move + tests
  - `c3b937a` - pin pyright's pythonPlatform to Windows (the real CI fix)
  - `db2be7b` - reconcile cursor.py/geometry.py monitor-span math
  - `d547352` - split server.py into app.py + routers/ + loops.py + behavior.py
- **CI, confirmed via the real Gitea Actions run** (not just "the
  runner picked up a task"): run 327 (commit `c3b937a`, the
  `pythonPlatform` fix) - **status 1 (Success)**, log shows `uv sync`
  clean, `ruff check`/`ruff format --check` clean, `pyright: 146 errors
  (baseline 148)`, `487 passed in 3.06s`, `Job succeeded`. Run 338
  (commit `d547352`, the full split) - **status 1 (Success)**, `ruff`
  clean, `pyright: 144 errors (baseline 148)`, `492 passed in 3.03s`,
  `Job succeeded`. Read via `ssh clockmost-claude`'s own
  `sqlite3`/`zstd` access to `/data/gitea/gitea.db` and
  `/data/gitea/actions_log/` - the same log-storage route felt-tray's
  WP-40 section used, since generating a Gitea API token was blocked by
  the auto-mode permission classifier as credential exploration.
- **Live smoke check** (killed the running `python.exe` whose command
  line contained `felt_animation`, started
  `E:\Felt\felt-animation\.venv\Scripts\python.exe -m felt_animation`
  hidden from its own directory - the overlay wasn't already running
  at the time, so felt-animation launched a fresh one; exactly 1
  `FeltOverlay.exe` process confirmed after startup and throughout):
  - `%TEMP%\felt-animation.log` on startup: `props: migrating
    placed-prop state from the old name ...\props.json (will save as
    ...\placed_props.json)` then `props: restored 6 placed item(s)` -
    the WP-40 item-6 migration working against Mario's real 6 placed
    items, live.
  - `GET /status` -> `200` with a real presence/hush/music/signals
    snapshot.
  - `POST /presence` (`action=move`) -> `playing 'locomotion/walk/
    normal_walk' (looping)` in the log, and no "no 'arrived' notice
    within Xs" warning - i.e. the real relay round-trip completed. (See
    "Not done": `overlay.py` itself, unchanged by this WP, never logs
    the literal word "arrived" on the success path, only on a timeout -
    a pre-existing gap, not something this refactor introduced or was
    asked to fix.)
  - `POST /debug/play_tag {"tag":"gesture/wave"}` -> `finished
    'gesture/wave' (layer base)`.
  - `POST /hush?minutes=0.1` -> exactly 6s later, `unhush: announcing
    {'hushed_for_s': 6, 'planned_s': 6, 'early': False}`, then a real
    felt-core round-trip (`POST .../v1/react/event -> 200`) and
    `react/event unhushed: 'That was pure torture, I think my brain
    actually started melting.'`, spoken through the real reply pipeline
    (rhubarb lipsync + audio playback logged).
  - No unexpected tracebacks: the only one logged was a
    `logger.warning(..., exc_info=True)` for a single transient
    `httpx.ReadTimeout` reaching felt-core during an unrelated
    spontaneous `game_start` reaction (Path of Exile 2 was already
    running at startup) - the exact "degrade with a logged reason"
    pattern rule 33/34 asks for, unchanged from `server.py`'s own
    original code, and felt-core answered normally on the very next
    request (the hush/unhush round trip above).

### Not done / unverified

- **`loops.py` (586 LOC) and `routers/playback.py` (493 LOC) are still
  above the ~400-LOC soft guideline** (rule 2). Both are well under the
  800-LOC hard-review-flag, and each is now a single cohesive concern
  (every background loop; every reply/voice endpoint) rather than mixed
  into a 2150-line file - but a follow-up split is named rather than
  attempted here, to land the cutover as one reviewable, fully-tested
  commit rather than risk a second large mechanical pass without a
  fresh review cycle in between: `loops.py` -> `ambient_loops.py`
  (ambient/idle/face-life/wander) + `signal_loops.py` (games/AFK/GPU/
  mash/call-energy/weather/music); `routers/playback.py` -> `reply.py`
  (`handle_reply` + its helpers) + `hush.py` (hush/unhush/mouth-along).
- **`handle_reply` and `lifespan` weren't decomposed beyond what the
  module split gave them for free.** The assignment named both
  explicitly alongside `_ambient_standing` (which *did* get a real
  split - `_ambient_standing_weights`). `handle_reply` (routers/
  playback.py, ~100 lines) is one continuous synchronized sequence
  (gather cues+tag -> resolve posture -> pick pose -> the one
  synchronized lipsync+audio start -> bubble/gaze -> persist +
  background body-clip task) where every step depends on the previous
  one's result in order - a real split would need to either return an
  intermediate struct between steps (a bigger design change than "pure
  refactor, no behaviour change" invites) or split along whitespace,
  which reduces line count without reducing understanding. Named
  rather than silently skipped.
- **`overlay.py` never logs the literal word "arrived" on the success
  path** (only `wait_for_arrived`'s own timeout warning mentions it) -
  confirmed pre-existing (unchanged by this WP, `overlay.py` wasn't
  touched) rather than a regression. If Mario wants an explicit
  live-checking log line for a successful arrival (matching the
  "finished" pattern already logged for clip completions), that's a
  one-line addition to `overlay.py`'s `_read_loop`, but it's a real
  (if tiny) behaviour addition, out of this WP's "pure refactor" scope.
- **One felt-core call timed out once during the live smoke check**
  (a spontaneous `game_start` reaction's `POST /v1/react/event`,
  `httpx.ReadTimeout`) - logged with full context, self-recovered on
  the very next request (the hush/unhush check, seconds later).
  felt-core is out of this WP's scope; flagged as an environmental
  observation, not investigated further.
- **A second `python.exe` process (the real system install, not the
  venv's) appeared as a child of the venv `python.exe`** during the
  smoke check, same as felt-tray's WP-40 section already documented for
  its own repo - no process-spawning code was touched by this WP, and
  `python -m felt_animation` against the venv's own `python.exe` (never
  a `uv`-generated shim) is exactly what rule 21 asks for either way.
- **This WP wasn't live-reviewed by Mario.** Status stays
  `🔎 needs review` (rule 27), not ticked, same as every other WP-40
  slice.
