# WP-39 — repo tooling: lint, format, types, pre-commit, CI

**Repos**: felt-core, felt-animation, felt-tray, felt-vision (full setup);
felt-character-assets (gdlint only); felt-dashboard (verify only);
felt-voice (read-only, noted, not touched). **Size**: L. **Depends on**:
WP-38 (this WP executes WP-38's "WP-39" items: #6, #7, #17, #23, #32 in
its ranked list, plus `ENGINEERING-RULES.md` §10).

## What / Why / Where

Wires up the tooling `ENGINEERING-RULES.md` §10 (rules 36-41) promised but
that didn't exist yet: ruff (lint+format) and pyright on every Python
repo, gdlint on the GDScript repo, and Gitea Actions CI everywhere,
matching felt-dashboard's oxlint/oxfmt/tsc/vitest `ci.yml` as the
reference. No behaviour changes anywhere — formatting, safe autofixes,
and config/CI are each their own commit per repo, and every repo's full
test suite passes before and after every commit.

### Python repos (felt-core, felt-animation, felt-tray, felt-vision)

Per repo: `uv add --dev ruff pyright pre-commit`; `[tool.ruff]`
(line-length 100, `target-version = "py312"`, `select =
["E","F","I","UP","B","SIM","C4"]`) and `[tool.pyright]`
(`typeCheckingMode = "basic"`) in `pyproject.toml`; `uv run ruff format`
as its own commit; `uv run ruff check --fix` (safe fixes only) as a
separate commit, with two trivial `assert False, msg` →
`raise AssertionError(msg)` rewrites folded in (ruff flags these but
doesn't autofix them; behaviourally identical under a normal, non
`-O` pytest run); remaining findings baselined via
`[tool.ruff.lint.per-file-ignores]` (list below) rather than risked;
`pyright`'s current error count recorded in a checked-in
`.pyright-baseline` integer, gated in CI by
`scripts/check_pyright_baseline.py` (fails only if the count *increases*);
`.pre-commit-config.yaml` (ruff-check --fix, ruff-format,
end-of-file-fixer, trailing-whitespace, plus a local
`scripts/check_env_example.py` hook diffing the repo's config module
against `.env.example` — felt-vision has no config module, so no such
hook there); `.gitea/workflows/ci.yml` (new for felt-animation,
felt-tray, felt-vision; extended for felt-core, which already had a
pytest-only one).

### The WP-38 mechanical gap items

- **felt-core** `.env.example`: added `FELT_GEMINI_API_KEY` (the actual
  cloud-enable switch), the legacy `FELT_GEMINI_CHAT_MODEL` override, the
  Home Assistant block (`FELT_HA_URL`/`_TOKEN`/`_ENTITIES`), and
  `FELT_HP_PRINTER_HOST` — all read by `config.py`, none previously
  documented. Key names only, no values.
- **felt-tray**: added `FELT_VISION_URL` (legacy fallback, had a hardcoded
  default but no `.env.example` entry) and rewrote the README's
  "felt-overlay lifecycle" section, which still described felt-tray
  launching `FeltOverlay.exe` via a `src/felt_tray/overlay.py` that
  hasn't existed since that ownership moved to felt-animation in WP-08.
- **felt-vision**: added `.env.example` (`OLLAMA_URL`, `VISION_MODEL`)
  and a real `README.md` (it had neither). Noted honestly that
  `main.py` reads both keys straight from `os.environ`, with no
  `python-dotenv` loading — copying `.env.example` to `.env` has no
  effect today; wiring that up is a new chore, not a WP-39 tooling
  change (would be a behaviour change).

### felt-character-assets (GDScript)

`gdtoolkit==4.5.0` (Godot 4 support) via `uv tool install`. New
`felt-godot-overlay/gdlintrc` excludes `addons/` (the vendored VRM
importer + MToon shader — not our code). **`gdformat` was not run** on
`main.gd` or `props.gd`, per this WP's explicit instruction (would clash
with WP-35's planned split and the `wp35-partial` stash). New
`.gitea/workflows/ci.yml` runs `gdlint` via `uvx`, **report-only**
(`continue-on-error: true`) — it surfaces the baseline without gating
merges.

### felt-dashboard

Verify-only, no changes. `package.json`'s `lint`/`fmt:check`/`typecheck`/
`test`/`build` scripts match `.gitea/workflows/ci.yml`'s steps exactly.

### felt-voice (Nitro5, read-only)

Not modified — access is read-only ssh (`ssh clockmost-nitro5`), no push
path, and it's the live voice service (never restarted). Inspected only:
it already has a bare `.gitea/workflows/ci.yml` (pytest-only, like
felt-core's before this WP) and **no** ruff/pyright/pre-commit config.
Flagged as a follow-up for whoever next has write access to that repo.

## Acceptance

- Every Python repo's full test suite passes, same count as this WP's
  baseline, before and after every commit (felt-core 359, felt-animation
  470, felt-tray 143; felt-vision has no test suite).
- `uv run ruff check`, `uv run ruff format --check`, and the pyright
  baseline gate all pass clean in felt-core/felt-animation/felt-tray/
  felt-vision.
- `uv run pre-commit run --all-files` passes clean in all four Python
  repos.
- `gdlint` runs clean against `felt-godot-overlay/gdlintrc`'s
  configuration (i.e. it runs and reports 268, not 0 — report-only, not
  a gate).
- Status set to `🔎 needs review` (rule 27) — none of this was
  live-reviewed by Mario.

### Proof

**felt-core** (commits `5868503`, `3a01102`, `5ec00dc`, `d5581b6`,
`b5a5089`, `65592dc`):
- `.env.example`: `FELT_GEMINI_API_KEY`, `FELT_GEMINI_CHAT_MODEL`,
  `FELT_HP_PRINTER_HOST`, `FELT_HA_URL`/`_TOKEN`/`_ENTITIES` added;
  verified 0 keys missing via `scripts/check_env_example.py`.
- `uv run ruff format`: 53 files reformatted. `uv run pytest -q` before
  and after: `359 passed`.
- `uv run ruff check --fix` (safe only): 9 fixed automatically, plus 2
  manual `assert False` → `raise AssertionError` rewrites
  (`tests/test_cloud.py:168`, `tests/test_react_screen.py:203`).
  `359 passed` after.
- Remaining baseline (all per-file-ignored, see `pyproject.toml`): E501
  ×23 across 13 files (plugin skills + `brain.py`/`cloud.py`/`db.py`/
  `events.py`/`music_taste.py`/`router.py`); B008 ×2 in `api.py`
  (FastAPI's `File()`/`Form()` dependency-injection idiom — a documented
  false positive, not a real issue); SIM105 ×4 (`brain.py` ×2,
  `test_metrics_audit.py`, `test_music_taste_loop.py`); SIM117 ×1
  (`ntfy_listener.py`). `uv run ruff check` → `All checks passed!` with
  these ignores in place.
- `uv run pyright`: **121 errors**, recorded in `.pyright-baseline`,
  gated by `scripts/check_pyright_baseline.py` (verified: exits 0 at
  exactly 121, would exit 1 above it).
- `.gitea/workflows/ci.yml` extended with ruff check, ruff format
  --check, and the pyright-baseline gate ahead of the existing pytest
  step.
- `git log --oneline -6` in felt-core, all pushed to `origin/main`
  (confirmed via `git push` output `3d5d363..65592dc main -> main`).

**felt-animation** (commits `25f61a1`, `52edbc1`, `d423306`, `9286061`):
- `uv run ruff format`: 58 files reformatted (+3 more after the lint-fix
  pass). `470 passed` before and after every commit.
- `uv run ruff check --fix`: 44 fixed automatically, plus 1 manual
  `assert False` → `raise AssertionError` (`test_beat_capture.py:54`).
- Remaining baseline (per-file-ignored): E402 ×9 across 7 files (one is
  the WP-38 item-18 `server.py:1382` mid-file import, explicitly left
  for that chore; `scripts/manual_reply_smoke.py` sets up its path
  before importing on purpose; the rest are tests importing after a
  fixture/monkeypatch block); E501 ×5 (`overlay.py`, `props.py`,
  `reaction.py`, `sounds.py`); B905 ×5 (`zip()` without `strict=` — a
  real behaviour question, not a mechanical fix); SIM102/105/108 ×4.
- `uv run pyright`: **148 errors**, recorded in `.pyright-baseline`.
- **Caught and reverted a real mistake**: `uv run pre-commit run
  --all-files`'s hygiene hooks initially reformatted two files under the
  vendored `rhubarb/Rhubarb-Lip-Sync-1.13.0-Windows/` release (tracked in
  git, not just `rhubarb.zip`) — reverted with `git checkout --
  rhubarb/` and excluded that path in `.pre-commit-config.yaml`
  (`exclude: '^rhubarb/'`) before committing anything.
- New `.gitea/workflows/ci.yml`, `runs-on: windows` (see Not done below).
- Pushed: `8eb270d..9286061 main -> main`.

**felt-tray** (commits `f3b9867`, `21185ff`, `1ac40b6`, `2b18eeb`):
- `.env.example`: `FELT_VISION_URL` added; verified via
  `scripts/check_env_example.py` (19/19 keys documented, up from 18).
  README's stale "felt-overlay lifecycle" section rewritten to describe
  the actual `POST /reply_ready` handoff to felt-animation.
- `uv run ruff format`: 17 files reformatted. `143 passed` throughout.
- `uv run ruff check --fix`: 15 fixed automatically.
- Remaining baseline: SIM105 ×2 (`capture.py`, `playback.py`); E501 ×3
  (`timing.py`, `test_capture_policy.py`, `tools/altgr_check.py`); C408
  ×1, C401 ×1 (test-only, cosmetic); **B023 ×1 in `tray.py:56`** —
  confirmed by reading the surrounding code to be a **false positive**:
  `(lambda cb: lambda: cb())(cb)` is the deliberate IIFE-capture idiom
  that already avoids the late-binding bug B023 warns about; ruff
  doesn't recognize the pattern. Documented in the per-file-ignore
  comment, nothing was "fixed" here because nothing is wrong.
- `uv run pyright`: **66 errors**, recorded in `.pyright-baseline`.
- New `.gitea/workflows/ci.yml`, `runs-on: windows` (see Not done below).
- Pushed: `aebfa97..2b18eeb main -> main`.

**felt-vision** (commits `258b8ca`, `8dc8203`, `72a1b04`, `de4570e`):
- `.env.example` + `README.md` added (both were missing/empty).
- `uv run ruff format`: 1 file reformatted (`main.py`). No test suite to
  run; verified the module still imports cleanly
  (`uv run python -c "import felt_vision.main"`) before and after every
  commit.
- `uv run ruff check --fix`: 1 fixed (import sort).
- Remaining baseline: B008 (FastAPI's own dependency-injection idiom,
  same false positive as felt-core's `api.py`) + E501 ×1, both in
  `main.py`.
- `uv run pyright`: **0 errors** — the cleanest of the four.
- `uv run pre-commit run --all-files` fixed one real trailing-whitespace
  line in `main.py` (hygiene hook, not ruff).
- New `.gitea/workflows/ci.yml`, `runs-on: ubuntu-latest` (this repo's
  deps — fastapi/httpx/uvicorn — are cross-platform, unlike
  felt-animation/felt-tray). No pytest step: no tests exist.
- Pushed: `eedba4d..de4570e main -> main`.

**felt-character-assets** (commit `74231ef`):
- `gdlint .` from `felt-godot-overlay` (via the new `gdlintrc`, `addons/`
  excluded): **268 findings** — `main.gd` 253 (165
  class-definitions-order, 72 max-line-length, 11 trailing-whitespace, 2
  function-argument-name, 1 enum-name, 1 loop-variable-name, 1
  max-file-lines), `props/props.gd` 14 (13 max-line-length, 1
  class-definitions-order), and `test_view.gd` **fails to parse
  entirely** (a leading BOM gdlint's parser chokes on) — consistent with
  WP-38 item 28 flagging it as dead/superseded code; not touched here.
- `gdformat` **not run** on `main.gd`/`props.gd` (explicit instruction).
- New `.gitea/workflows/ci.yml`: `gdlint` via `uvx --from "gdtoolkit==4.*"`,
  `continue-on-error: true` (report-only).
- Pushed: `d7ca5ee..74231ef main -> main`.

**felt-dashboard** (verify-only, no commit):
- `pnpm typecheck`, `pnpm test` (7 passed), `pnpm build` all pass clean,
  matching `.gitea/workflows/ci.yml`'s steps exactly.
- **`pnpm lint` (oxlint --deny-warnings) currently fails**: 2 real
  `no-underscore-dangle` warnings on `__feltReloadHistory`
  (`src/App.tsx:68,72`), turned into a hard failure by
  `--deny-warnings`. This contradicts `docs/ARCHITECTURE.md`'s "already
  enforced and green" note — the audit's claim doesn't hold today.
  **Not fixed** (out of this WP's scope — felt-dashboard's own task was
  verify-only, and touching `App.tsx` isn't a "tooling" change).
- `pnpm fmt:check` also reports 22 files needing reformatting on this
  Windows checkout, but that's a false alarm from this desktop's global
  `git config core.autocrlf=true` converting the repo's LF blobs to CRLF
  on checkout — oxfmt/oxlint (Rust/oxc-based) expect LF and flag the
  CRLF conversion as a diff. Confirmed: `git status` was clean before
  touching anything, and `grep -c $'\r' src/App.tsx` → 0 on the
  git-tracked blob, `file src/App.tsx` → CRLF on the checked-out working
  copy. The real Gitea Actions runner checks out on Linux (no autocrlf),
  so this specific finding is **not** expected to reproduce there — only
  the `no-underscore-dangle` lint failure is real and would fail on
  Linux CI too.

**CI runner** (read-only, via `ssh clockmost-claude`):
- A Gitea Actions runner **is** registered and active:
  `gitea-act-runner` (container `Up 24 hours`), confirmed via
  `docker compose.yaml` and `runner_data/.runner` (id 3, name
  `gitea-act-runner`). Labels: `ubuntu-latest`, `ubuntu-22.04` (both
  `catthehacker/ubuntu:act-latest`), `archlinux` (`archlinux:base-devel`)
  — **all Linux**, no Windows label.
- It's already actively running CI for `Benylin/felt-core` (8+ runs over
  the last 24h), `Benylin/felt-voice` (2 runs), and `Benylin/felt-dashboard`
  (1 run) — confirmed via `docker logs gitea-act-runner`.
- **No runner was set up or touched** — per this WP's explicit
  instruction, since one already exists.

### Not done / unverified

- **felt-animation and felt-tray's new CI cannot go green on the
  existing runner.** Both repos depend on Windows-only packages with no
  Linux wheels (felt-animation: `comtypes`, `pyaudiowpatch`, `pycaw`,
  `wmi`; felt-tray: `windows-capture`, `winotify`, plus `keyboard`/
  `pywebview` which need a desktop/display). `uv sync` cannot succeed on
  the registered runner's Linux-only labels. Their `.gitea/workflows/
  ci.yml` files are written and correct (per WP-39's instruction to
  write them anyway), targeting `runs-on: windows`, but **will sit
  queued indefinitely** with no matching runner. **What's needed**: a
  Windows-capable Gitea Actions runner — the natural candidate is a
  self-hosted `act_runner` on the desktop (CLOCKMOST) itself, registered
  against `git.clockmost.com`, since that's the only Windows box in this
  setup and it's where these repos actually run. This is a
  desktop/infra change, explicitly out of scope for this WP (told not to
  set up a runner) — flagging it as the concrete next step rather than
  a vague "needs a runner."
- **No non-hermetic tests were found** in felt-core, felt-animation, or
  felt-tray — every suite ran clean, full-speed, with no network access
  beyond felt-core's already-hermetic VCR cassettes (default
  `record-mode=none`, replays only). This wasn't an exhaustive
  line-by-line audit of every test; it's a full green run of each suite
  in this sandboxed session (no real `.env`, no felt-voice/Ollama/
  felt-animation processes actually running) plus targeted greps for
  `os.environ[`, hardcoded ports, and skip markers. If a genuinely
  environment-dependent test exists that happens to degrade gracefully
  rather than fail loudly when its dependency is absent, this pass
  wouldn't have caught it.
- **felt-voice was not modified** — read-only ssh access only, no push
  path from this session. It already has a bare pytest-only `ci.yml` and
  no ruff/pyright/pre-commit; ENGINEERING-RULES.md rule 36 lists it
  among the repos ruff should cover, so this is a real, named gap for
  whoever next has write access there (not "forgotten" — see the What
  section above).
- **felt-dashboard's lint failure was reported, not fixed** (out of
  this WP's verify-only scope for that repo). Mario should decide
  whether to fix the two `__feltReloadHistory` warnings, allow-list the
  rule, or drop `--deny-warnings`.
- **Pyright baselines were recorded, not triaged.** None of the 121
  (felt-core) / 148 (felt-animation) / 66 (felt-tray) errors were looked
  at individually beyond a handful spot-checked while writing this
  section (mostly `reportArgumentType`/`reportOptionalMemberAccess` in
  test fakes/mocks). A future WP should actually triage these, not just
  gate on the count staying flat.
- **The E501/SIM105/etc. per-file-ignores are a baseline, not a
  decision that these are fine forever** — see each repo's Proof section
  above for the exact list; a future chore (not named as a WP yet) should
  work through them file by file.
- **This WP wasn't live-reviewed by Mario.** Status set to
  `🔎 needs review` per rule 27, not ticked.

## Follow-up: felt-core continuous deployment (Mario, 2026-09-26)

"This needs to be automated as it was intended, we might need to implement
some middleware, but the plan was always push to master -> builds ->
deploys."

**Design** (to be built right after WP-40, so it doesn't collide with the
brain.py split):
- **Trigger and gate:** a `deploy` job in felt-core's `.gitea/workflows/`,
  on push to `main`, `needs: ci` (tests + ruff + pyright green), on the
  server's Linux runner.
- **Export:** `git -c core.autocrlf=false archive HEAD`. This permanently
  fixes the CRLF vendoring problem.
- **Vendor:** replace `projects/felt-core/app/` in a clone of
  clockmost-infra, then commit ("felt-core: <sha> <subject>") and push as a
  bot.
- **Token:** a dedicated Gitea deploy token (or deploy key) with write
  access to clockmost-infra only, stored as a runner secret. The job
  touches only that path.
- **Deploy:** the existing `clockmost-deploy` loop takes over unchanged:
  backup check → deploy → health check → auto-revert plus an ntfy URGENT
  alert on failure.
- **Later:** trigger `clockmost-deploy.service` immediately instead of
  waiting up to 10 min.
- **Proof:** a trivial felt-core commit shows up live without anyone
  touching the server.

## Follow-up: switch the type checker to Astral `ty` (Mario, 2026-09-26)

"Also use Astral TY instead of pyright."
- Replace pyright with `ty` in every Python repo: the dev deps (`uv add --dev
  ty`, `uv remove --dev pyright`), pre-commit, and the CI workflows.
- Take a fresh baseline with ty; its counts won't match pyright's. Gate it
  the same way, so CI fails only on *new* errors.
- **When:** right after WP-40 lands, together with the felt-core CD job.
  The three WP-40 refactor agents keep the pyright baseline as their
  "no new errors" check until then, so the tool isn't swapped mid-refactor.
- Check ty's current config and CLI (it's newer than pyright) when doing
  the swap.
- **Zero-error policy** (Mario, 2026-09-26: "you should fix all errors that
  ty point out, not just new ones").
  - The ty pass fixes **every** error in every repo; no baseline file.
    Tests must stay green after each batch.
  - Genuine false positives get **inline** suppressions with a reason
    (`# ty: ignore[<rule>]  # why`).
  - CI then fails on any type error.
  - Same for ruff: the WP-39 leftovers (E501, SIM, E402, B905…) get fixed.
    Only documented false positives stay as inline ignores (FastAPI
    `File()`/`Form()` B008, the IIFE capture B023 in felt-tray `tray.py`).
  - Fixes stay typing-only where possible. Any fix that changes logic gets
    flagged in the notes and covered by a test.
