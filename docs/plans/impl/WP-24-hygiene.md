# WP-24 — Repo hygiene

**Repos**: AnimToVrmaConverter, felt-character-assets, felt-vision,
felt-core. **Size**: S. **Depends on**: none (it can run any time between
other WPs).

## Changes

### AnimToVrmaConverter
- It's tracked in git, and shouldn't be:
  - four UniVRM/VRM `.unitypackage` files (~100 MB): `UniVRM-0.128.0_264a`,
    `UniVRM-0.131.2`, `VRM-0.128.0_264a`, `VRM-0.131.2`;
  - ~20 `unity_*.log` files (root and under `My project/Assets/`);
  - `My project/Assets/TempCLI/StandIdle.unitypackage`.

  `git rm --cached` them (keep the files on disk). Add a `.gitignore`:
  `*.log`, `*.unitypackage`, and explicitly `Movement Animset Pro*.unitypackage`
  (a **paid asset, must never be pushed**), plus the loose converted
  `MovementAnimsetPro_*.vrma` outputs once WP-18 has copied what it needs
  into the library (or move them to an ignored `output/` folder). Also Unity's
  `Library/`, `Temp/`, `Logs/`, `obj/` if not already ignored.
- Uncommitted edits exist in `Convert-AnimToVrma.ps1` and
  `My project/Assets/Editor/VrmaCliConverter.cs`. Read the diff, and **ask
  Mario** whether they're his or a previous agent's work in progress before
  committing or discarding. Don't discard.
- Note in the README that the history still contains the big files. Rewriting
  history is **not** part of this WP; mention it to Mario as an option only.

### felt-character-assets (main.gd)
- Remove dead code:
  - the `_unhandled_input` number-key/`test/…` branches (the click-through
    overlay never receives key input);
  - the `SMALL_TEST_WINDOW_FOR_TESTING` flag.

  **Keep `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING` until WP-22** (that WP
  removes it), and keep `CAPTURE_SCREENSHOT_FOR_TESTING` (it's used for visual
  checks).
- `all_bones.txt` (586 lines at the overlay root): if it's a stale debug dump,
  move it to `docs/` or delete it. Check it isn't referenced first.

### felt-vision
- Write a real `README.md` (currently empty): what it is, that it's now the
  local fallback describer behind WP-07, env vars, run command.
- Add `.env.example` + `python-dotenv` loading, like the sibling repos
  (`OLLAMA_URL`, `VISION_MODEL`).

### felt-core
- `api.chat_ws` swallows every exception silently: log it
  (`logger.exception`) before closing.
- `load_plugins()` rescans the plugins dir on every message. Cache the
  registry and reload only when the directory's mtime changes.

## Acceptance
- `git status` is clean in each repo after committing, and the AnimToVrma repo
  no longer tracks packages or logs.
- The Godot overlay still builds and runs.
- felt-core tests are green, and it's deployed if felt-core changed.
