# Tooling pass, 2026-09-27 — ty swap + zero-error policy

Executes the two follow-ups WP-39 recorded but didn't do (`WP-39-tooling.md`'s
"Follow-up: switch the type checker to Astral `ty`" and the zero-error policy
now in `ENGINEERING-RULES.md` §10/"Zero-error policy"/"Type-safe code, not
silenced code"): replace pyright with Astral ty on every Python repo, fix
every ty error for real (no baseline), and take ruff's WP-39 per-file-ignore
baselines to zero. Each repo's agent owns its own section below - `git pull
--rebase` before appending a new one.

## felt-tray

**ty**: 60 errors -> 0. No suppressions needed for any of the 60 - every one
fixed with real types/narrowing instead:
- `app.py`: `_run_poll_loop`'s `interval: float | Callable[[], float]` param
  replaced with plain `Callable[[], float]` - `callable()` can't be narrowed
  soundly under the int/float numeric tower (ty correctly refused to treat
  the post-narrowing branches as `float`), so the union itself was the bug,
  not the check. Both call sites now pass a zero-arg callable (one just
  returns the fixed interval).
- `mic.py`: narrowed `on_pause` itself (not just `self._detector`) before
  calling it inside the audio callback - `self._detector` is only ever
  constructed when `on_pause` was truthy, but that's a link between two
  different closure variables ty can't trace, so `on_pause` gets its own
  `is not None` check too. Logic-preserving (the call was already
  unreachable when `on_pause` is None).
- `watcher.py`: `_save_debug_jpeg` takes `debug_dir: str` as a plain
  parameter instead of re-reading `self.debug_dir: str | None` - the
  caller's `if self.debug_dir:` narrowing doesn't cross the method
  boundary.
- `window.py`: `ChatWindow.__init__` raises `RuntimeError` if pywebview's
  own `create_window() -> Window | None` stub returns `None`, instead of
  threading `Optional` through every method that uses `self._window`.
  **Logic-touching** (a new, narrow failure path that didn't exist before -
  the old code would have hit an `AttributeError` on the next line instead).
  Covered by new `tests/test_window.py` (1 test, monkeypatches
  `webview.create_window` to return `None`).
- `capture_win32.py` / `toast.py`: their existing Windows-only-import
  guards (`windows_capture`, `winotify`) swapped from
  `# pyright: ignore[reportMissingImports]` to
  `# ty: ignore[unresolved-import]` - genuinely needed on the Linux CI
  runner (the sys_platform marker means `uv sync` never installs either
  package there) but flagged as **unused** on this Windows dev box (where
  both resolve normally) - ty, unlike pyright, hard-fails by default on an
  unused ignore. `unused-ignore-comment` downgraded to `"ignore"`
  project-wide in `pyproject.toml`'s new `[tool.ty.rules]` (these two lines
  are the only ignores in the repo; the rule itself never hides a real type
  error, only ty's own "is this suppression still needed" meta-check).
- Tests: every `app._client = _FakeClient(...)`-shaped swap
  (`test_app_delivery.py`, `test_capture_order.py`, `test_music_poll.py`,
  `test_tray_rebind.py`) now **subclasses the real collaborator**
  (`FeltCoreClient` / `ChatWindow` / `Recorder` / `HotkeyManager` /
  `BackchannelDetector`) instead of a standalone duck-typed class, so the
  assignment type-checks nominally with zero ignores - none of these fakes
  call `super().__init__()`, so no real HTTP client/pywebview
  window/Win32 hotkey/mic stream is ever created. Two direct
  instance-level method swaps (`_rebind_action`, `_on_screen_reaction`)
  moved to `monkeypatch.setattr(Class, "method", lambda self, ...: ...)`
  at the class level, matching the method's real `(self, ...)` signature -
  a bare `lambda action, label: ...` assigned straight onto an instance
  doesn't type-check against a method name, even though it's exactly what
  runs at that call site. `test_capture_policy.py`'s `_felt_chat_window`
  takes named parameters instead of `**kw`-unpacking a plain `dict` into
  `WindowInfo` - a dict's values collapse into one union type ty correctly
  can't verify field-by-field against the dataclass. `test_capture_order.py`
  swapped its `client=None`/`blocklist=object()` sentinels for real (but
  unused - both are monkeypatched away in these ordering-only tests)
  `FeltCoreClient`/`Blocklist()` instances.

**ruff**: the WP-39 baseline (SIM105 x2, E501 x3, C408, C401, B023) -> 0.
Every finding fixed for real (`try/except/pass` -> `contextlib.suppress`,
four wrapped long lines/strings, a generator -> set-comprehension rewrite)
except the one documented false positive: `tray.py`'s
`(lambda cb: lambda: cb())(cb)` IIFE-capture idiom, which already avoids
the late-binding bug B023 warns about - kept as an inline `# noqa: B023`
at its own line with the reason, not a per-file ignore.

**CI**: `.pyright-baseline` and `scripts/check_pyright_baseline.py` deleted;
`.gitea/workflows/ci.yml`'s types step now runs `uv run ty check` directly
(no baseline gate). Confirmed on the real runner
(`ssh clockmost-claude`, `gitea-act-runner`'s own `actions_log`, task 433):
`ruff check` / `ruff format --check` / `ty check` all "All checks passed!",
`153 passed in 1.28s`, `Job succeeded`.

**Tests**: 152 -> 153 (the one new `test_window.py` case). Full suite green
throughout, re-run after every commit.

**Commits** (`git.clockmost.com:Benylin/felt-tray.git`, pushed to
`origin/main`): `938687b` (ty swap + every type error fixed), `b58301c`
(ruff to zero, baseline removed).

### Proof

- `uv run python -m pytest -q`: 153 passed (before: 152).
- `uv run ruff check` / `uv run ruff format --check`: clean.
- `uv run ty check`: `All checks passed!` (before: 60 diagnostics).
- `uv run pre-commit run --all-files`: clean (ruff-check, ruff-format,
  end-of-file-fixer, trailing-whitespace, check-env-example all Passed).
- CI, real runner log (`/home/clockmost-infra/projects/gitea/gitea_data/
  gitea/actions_log/Benylin/felt-tray/b1/433.log.zst`, task 433, commit
  `b58301c`): ruff check/format clean, `ty check` -> "All checks passed!",
  `153 passed in 1.28s`, `Job succeeded`.
- **Live smoke check** (killed both `python.exe` processes with
  `felt_tray` in their command line - the venv one and the pywebview-
  spawned system-Python child WP-40 already documented as a pre-existing
  quirk - then started `E:\Felt\felt-tray\.venv\Scripts\python.exe -m
  felt_tray` hidden from its own directory): `F:\Temp\felt-tray.log` shows
  `hotkeys registered: {..., 'clean': 'ctrl+shift+X'}` (the `ctrl+shift+X`
  rebind present), `Desktop Watcher started.`, and a real capture decision
  with blocklist reasons - `watcher: decision trigger=focus
  target=pathofexilesteam.exe rejected=[feltoverlay.exe:felt-pidx2,
  firefox.exe:process, discord.exe:process]` (Path of Exile 2 was already
  running; Discord/Firefox correctly excluded) - followed by a real
  end-to-end reaction round-trip (`POST .../v1/react/screen -> 200`). No
  tracebacks anywhere in the new log lines. Both the venv `python.exe` and
  the same pywebview-child-process quirk (system Python, `-m felt_tray`)
  came back after the restart - confirmed pre-existing (WP-40's own notes),
  not something this pass touched.

### Not done / unverified

- The 42 test-only `__new__`-bypass fakes were fixed by subclassing rather
  than by introducing Protocols for `App`'s collaborators - simpler and
  zero production-code impact, but it does mean a future fake that
  forgets to skip `super().__init__()` could accidentally construct a real
  `httpx.Client`/pywebview window/Win32 hotkey hook. Not a new risk this
  pass introduced (the previous duck-typed fakes had the analogous risk of
  silently drifting from the real interface with nothing to catch it) -
  just naming the tradeoff.
- Not live-reviewed by Mario (ENGINEERING-RULES.md rule 27) - this is a
  tooling-only pass with no product behavior change beyond the two named
  logic-touching fixes (`window.py`'s None-guard, already covered by a
  test); flagging per the same convention as every other WP anyway.

## felt-vision

**ty**: 0 -> 0 (already the cleanest of the four repos under pyright per
WP-39; stays 0 under ty).

**ruff**: 2 (B008, E501, both per-file-ignored) -> 0. E501 fixed for real
(the `SYSTEM_PROMPT` triple-quoted string's one over-length line split
across backslash-continuations - verified byte-identical at runtime via
`repr(SYSTEM_PROMPT)` before/after, since a backslash-newline inside a
string literal drops the newline rather than inserting one). B008 kept as
a documented inline `# noqa` (FastAPI's own `File()`/`UploadFile`
dependency-injection idiom - the "fix" ruff suggests would break the
framework contract, same false positive already accepted for felt-core's
`api.py`).

**Typed models** (`ENGINEERING-RULES.md`'s "typed models for relay
messages/API bodies... not loose `dict[str, Any]`"): `main.py` gained
`OllamaGenerateRequest`/`OllamaGenerateResponse` (`TypedDict`, for the
Ollama `/api/generate` call) and `AnalyzeResponse` (a pydantic
`BaseModel`, wired as `/analyze`'s `response_model`) for the
`{"description": str}` body felt-tray's `watcher.py` parses on the other
end. `pydantic` added as an explicit dependency (it was only ever present
transitively via `fastapi`). `run()` annotated `-> None`.

**Tests**: felt-vision had none at all (WP-39's own notes named this gap
explicitly). Added `tests/test_analyze.py` (3 tests, `pytest` + dev dep):
the config defaults (`OLLAMA_URL`/`VISION_MODEL`), and `/analyze`'s
request/response shape end-to-end via FastAPI's `TestClient`, with
`httpx.AsyncClient.post` monkeypatched - no real Ollama needed for either
the success or the 503-unreachable path.

**CI**: `.gitea/workflows/ci.yml`'s types step now runs `uv run ty check`
(previously `uv run pyright`, no baseline existed either way); added a
`pytest` step (previously none - "no tests exist yet"). README's dev
command block and test-suite note updated to match.

**Commit** (`git.clockmost.com:Benylin/felt-vision.git`, pushed to
`origin/main`): `8601918` - one commit for this repo (ty swap, ruff to
zero, typed models, and the new smoke tests all landed together; the repo
is small enough - one 90-line module - that splitting further would have
meant surgical same-file hunk splits with no real revertability benefit).

### Proof

- `uv run python -m pytest -q`: 3 passed (before: no test suite existed).
- `uv run ruff check` / `uv run ruff format --check`: clean.
- `uv run ty check`: `All checks passed!` (unchanged - 0 before, 0 after).
- `uv run pre-commit run --all-files`: clean.
- CI, real runner log (`.../actions_log/Benylin/felt-vision/b2/434.log.zst`,
  task 434, commit `8601918`): ruff check/format clean, `ty check` ->
  "All checks passed!", `3 passed, 2 warnings in 0.63s` (the warnings are
  Starlette/anyio's own deprecation notices, not this repo's code),
  `Job succeeded`.

### Not done

- No live smoke check for felt-vision specifically (not asked for - the
  task's live-smoke-check instruction named felt-tray only). The new
  tests exercise `/analyze` against a monkeypatched Ollama, not a live
  `felt-vision` process talking to a real Ollama instance.
- `main.py`'s `/analyze` still has no real request-body validation beyond
  FastAPI's own `UploadFile` handling - out of scope for a tooling pass
  (would be a behavior change, and WP-38 item 33's planned `/health`
  endpoint is the named place for that kind of follow-up).
- Not live-reviewed by Mario (rule 27).
