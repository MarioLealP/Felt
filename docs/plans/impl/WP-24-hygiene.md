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

## Status (2026-09-27)
- **AnimToVrmaConverter** `4c60c1a`:
  - 24 `.unitypackage`/`.log` files are untracked (`git rm --cached`; the
    files are still on disk);
  - `.gitignore` gained `*.log`, `*.unitypackage`, an explicit rule for the
    **paid Movement Animset Pro** pack (verified with `git check-ignore`),
    and the loose root `MovementAnimsetPro_*.vrma`/`MaskmanFace_*.vrma`
    outputs;
  - the README notes that history still has the big files (a rewrite is an
    option only);
  - the remote is private Gitea.
- **Still open, and it's Mario's call:** uncommitted edits in
  `Convert-AnimToVrma.ps1` + `VrmaCliConverter.cs`.
  - They date from **09-22**, before the 09-26 WP-18B "multi-take FBX
    converter" commit.
  - They comment out the package import, hardcode a `MovementAnimsetPro`
    folder, and add per-clip multi-export. This looks like an earlier
    agent's hack that WP-18B superseded.
  - Also untracked and left alone: `My project (1)/` (a whole project copy)
    and the imported asset folders `!dalha_はなみず/` and `=1000=/`.
- **main.gd** `0aed5c5`: the dead `_unhandled_input` number-key/test
  handler is removed (27 lines). `SMALL_TEST_WINDOW` was already gone. The
  stale `all_bones.txt` (an old UTF-16 Godot console log, unreferenced) is
  deleted. The export builds clean.
- **felt-vision** `7db4cb5` → `a74f525`: the repo-root `.env` loads via
  **pydantic-settings** (`VisionSettings`). Mario: "use pydantic-settings
  instead of pythondotenv". The process env still wins. README and
  `.env.example` are updated. The README had already been written.
- **felt-core:** `chat_ws` logging was already done (the rules-33/34 audit).
  **Plugin registry cache** `31d27d1`: it rescans only when a manifest or a
  plugin's `skill.py` changes (keyed on file mtimes, because a dir mtime
  misses edits inside subfolders). The test is `test_plugin_cache.py`.
- **Closed 2026-09-27.** Mario: "feel free to delete whatever isnt used".
  Auto mode blocks agent deletes, so Mario ran them:
  - the WIP was stashed (`stash@{0}`);
  - the 208 loose root `.vrma` outputs, `My project (1)/` and the
    re-importable `!dalha_はなみず` pack were deleted.
  - **Kept:** `=1000=` (no other copy exists). The imported packs
    (Kipfel, Tako.S, MovementAnimsetPro, Violet) are source material and are
    now **gitignored**, so paid content can't be pushed (`c0d9a55`).
  - AnimToVrma `git status` is clean.
