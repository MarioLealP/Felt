# WP-01 — felt-animation: unknown-tag freeze fix, file logs, test suite

**Repos**: `E:\Felt\felt-animation`, `E:\Felt\felt-character-assets`
(main.gd), `E:\Felt\felt-vision` (logging only). **Size**: S. **Depends on**:
none.

## Why

felt-core sends animation tags that don't exist in the desktop library. For
example, `get_weather` emits `reaction/weather/sun|rain|storm|snow`, and there
is no `reaction/weather` folder. `server.py::_handle_reply` skips its own
classifier whenever a tag is supplied, plays the missing tag, and
`OverlayClient.play_and_wait` then waits the full `CLIP_TIMEOUT` (30 s),
because main.gd never sends `finished` for a tag with no clips. While waiting,
it **holds the activity lock**, so she freezes and ambient stops. That happens
after every weather answer. Separately, felt-animation and felt-vision run
hidden and log only to a console that doesn't exist, and felt-animation has
zero tests even though `state.py` has already had one race bug.

## Changes

### 1. Tag resolution (felt-animation, `library.py`)
Add a pure function:
```python
def resolve_known_tag(tag: str | None, known_tags: set[str]) -> str | None:
    """Exact match, else walk up the path ('a/b/c' -> 'a/b' -> 'a') to the
    nearest ancestor that is a real tag; None if nothing matches."""
```

### 2. Use it in `server.py::_handle_reply`
Run it before `resolve_posture_tag`:
- `animation_tag = library.resolve_known_tag(animation_tag, known_tags)`
- If the result is `None` (the supplied tag was unknown, or none was
  supplied), fall through to the existing `classify_reaction(...)`.
- Log at INFO when a tag was broadened (`'reaction/weather/sun' ->
  'reaction'`) or dropped to the classifier.

### 3. Defence in depth in the overlay (`main.gd::_play_tag`)
When `tag_to_clips` has no entry for the tag (or the entry is empty),
immediately `_broadcast_to_relay({"finished": tag, "missing": true})`
before returning. Any path that still sends an unknown tag (ambient, future
code) then gets released in milliseconds instead of 30 s. In
`overlay.py::_read_loop`, log a WARNING when `missing` is true. Rebuild the
overlay afterwards (see the context doc: direct Godot export, not
UpdateFelt, unless you intend to commit through it).

### 4. File logging
- `felt-animation/src/felt_animation/server.py`: replace
  `logging.basicConfig(level=logging.INFO)` with the same pattern felt-tray
  uses (`felt-tray/src/felt_tray/__init__.py`): a `FileHandler` to
  `%TEMP%\felt-animation.log` (utf-8) + `StreamHandler`, with the format
  `%(asctime)s %(levelname)s %(name)s: %(message)s`.
- `felt-vision/src/felt_vision/main.py`: same, to `%TEMP%\felt-vision.log`.
- Make sure uvicorn's own loggers still show (don't pass `log_config=None` in
  a way that drops them).

### 5. Test suite (felt-animation)
- `uv add --dev pytest pytest-asyncio`. Add `[tool.pytest.ini_options]
  testpaths = ["tests"]`, `asyncio_mode = "auto"` to `pyproject.toml`.
- Move `test_api.py` (a manual smoke script, not a test) to
  `scripts/manual_reply_smoke.py`.
- Add `tests/`:
  - `test_library.py`: `scan_tags` on a `tmp_path` tree (a folder with only
    subfolders is *not* a tag; `.vrma.import` counts); `resolve_known_tag`
    (exact, one level up, several levels up, nothing, `None` input);
    `resolve_posture_tag` (standing; sitting with a `/sitting` variant;
    sitting without one → needs stand-up).
  - `test_state.py`: `BehaviorState` with a fake overlay whose `play_and_wait`
    records calls and awaits a tiny sleep. Cases: `run_sequence` holds the
    lock (`busy` is True during it); `begin_thinking("idle")` is a no-op;
    **the race regression**: `begin_thinking(tag)` immediately followed by
    `end_thinking_and_wait()` (before the task runs) must terminate and not
    loop forever (use `asyncio.wait_for(..., 2)`).
  - `test_expressions.py`: `_expression_for_tag` returns weights for
    `emotion/laughing`, `reaction/stumble`, and `None` for `idle`. Import from
    `server` carefully: importing `server` calls `load_config()` at module
    import, which requires `.env`. Either move `_EXPRESSION_KEYWORDS` /
    `_expression_for_tag` into a new `expressions.py` (preferred, and update
    the import in `server.py`), or set the env vars in `conftest.py`.

## Acceptance (do all of these)

1. `uv run pytest -q` in felt-animation passes.
2. With Felt running (Launch Felt), send a fake weather reply:
   ```powershell
   curl.exe -X POST http://127.0.0.1:8421/reply_ready -F "text=It's sunny and 24 degrees" -F "animation_tag=reaction/weather/sun"
   ```
   `%TEMP%\felt-animation.log` shows the tag being broadened or dropped to
   the classifier, and a real clip plays within ~2 s. There's **no**
   "no completion notice … within 30.0s" warning.
3. Send `{"tag": "does/not/exist"}` straight to the overlay
   (`python -c "import socket; s=socket.create_connection(('127.0.0.1',8765)); s.sendall(b'{\"tag\":\"does/not/exist\"}\n')"`)
   while felt-animation is connected. felt-animation's log shows the
   `missing` warning.
4. `%TEMP%\felt-vision.log` gets lines when felt-vision starts.

## Out of scope

Changing which tags felt-core sends (weather clips come later in WP-18),
mood logic, playback.

## Notes from implementation (2026-09-22)

Implemented as specced. Commits:
- felt-animation: `b9a17df` — `library.resolve_known_tag()`, wired into
  `_handle_reply` before `resolve_posture_tag`; file logging for both
  felt-animation and felt-vision; `expressions.py` split out of
  `server.py` so `_expression_for_tag`/`_EXPRESSION_KEYWORDS` (renamed
  `expression_for_tag`) are testable without `.env`; `tests/` with 17
  passing cases (`test_library.py`, `test_state.py` incl. the race
  regression, `test_expressions.py`); `test_api.py` → `scripts/
  manual_reply_smoke.py`; `pyproject.toml` gets `[tool.pytest.ini_options]`.
- felt-vision: `eedba4d` — same file-logging pattern, plus a startup
  `logger.info` line (needed for acceptance check 4 — without an
  explicit log call at import time there was nothing to see in the file
  even though it was created and working).
- felt-character-assets: `86c071f` — `_play_tag` broadcasts
  `{"finished": tag, "missing": true}` for both the "no entry in
  tag_to_clips" and "entry exists but empty" cases; `overlay.py`'s
  `_read_loop` logs a WARNING when `missing` is true. Rebuilt via direct
  Godot export (not UpdateFelt.ps1).

Deviations / notes:
- A concurrent Antigravity/Gemini session was live-editing
  `felt-character-assets/main.gd` at the same time (garment-swap +
  screenshot-hook code, unrelated to this WP — confirmed with Mario
  mid-session, "I forgot i had gemini churning in the background").
  First attempt at committing the WP-01 hunk with `git commit -- <path>`
  silently re-staged the *whole* working-tree file from disk (git's
  pathspec-commit behavior, not `git add`'s), pulling in ~75 lines of
  that unrelated in-progress code. Caught it in the follow-up `git show
  --stat`, reset with `git reset --soft HEAD~1`, and re-split into two
  commits: `86c071f` (just the two `_broadcast_to_relay` lines) and a
  separate `52dcdf1 [gemini-wip] ...` commit carrying the garment/
  screenshot code on its own, labeled so it's a clean `git revert`
  target if that in-progress feature isn't wanted as-is (Mario, mid-
  session: "Feel free to partial commit gemini stuff, clearly indicating
  its gemini stuff... so you dont have to skirt around it every commit").
  Lesson for future WPs touching a file Gemini/OpenHands might also be
  editing: never `git commit -- <path>` when only part of that path's
  diff is staged — it re-adds the whole working-tree version first.
  `git commit` with no pathspec commits exactly the index.
- Acceptance checks 1-4 all verified live: `uv run pytest -q` (17
  passed), the weather-tag POST logged "dropping to the local
  classifier" with no 30s timeout warning, a raw unknown tag sent to
  :8765 logged the `missing` WARNING, and felt-vision.log got the new
  startup line. Felt was left stopped afterward (Mario: fine to leave
  her off between test runs).
- `known_tags` at scan time (34 tags) has no `reaction/weather` or
  `reaction/weather/*` — confirms the freeze this WP fixes was real and
  not hypothetical; `emotion/*`, `gesture/*` etc. all present and
  correctly picked up by `resolve_known_tag`'s ancestor walk.
