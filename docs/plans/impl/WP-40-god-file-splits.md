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
