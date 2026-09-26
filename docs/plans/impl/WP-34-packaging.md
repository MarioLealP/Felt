# Phase 7 — Packaging: one clean install per device (WP-34)

Read `00-implementer-context.md` first. **This is the last WP.** It runs
after every other WP is ticked (WP-19 included, once its deep dive is
done), so it packages the finished system and not a moving target.

Mario, 2026-09-26: "bundle everything desktop side into a single exe on the
tray, including the ollama stuff and etc, without weird cmds running and
what not. Same for the other devices, so after we finish everything we can
tie it with a nice bow, where it's just the necessary stuff for a fresh
install."

---

## WP-34

### One app per device, and a fresh install is just "install it"
**Repos:**
- felt-tray (becomes the desktop host)
- felt-animation
- felt-character-assets (overlay build)
- felt-voice
- felt-core / clockmost-infra
- a new `felt-installer` (or a folder in the umbrella repo)

**Size:** XL. It will probably split into 34a (desktop), 34b (Nitro5) and
34c (server + fresh-install runbook). **Depends on:** everything else.

**Today's sprawl (inventory, 2026-09-26). This is the list to get rid of.**

| Device | What runs now | How it starts |
|---|---|---|
| Desktop | felt-animation (python) | `LaunchFelt.ps1` → hidden `python -m felt_animation` |
| Desktop | Godot overlay `FeltOverlay.exe` + `.pck` | started by felt-animation |
| Desktop | click-through patch | a **hidden PowerShell** `patch-clickthrough.ps1 -TargetPid …` |
| Desktop | felt-vision (llava describer) | `LaunchFelt.ps1`. Probably dead since WP-06/07 (Gemma vision): verify and delete |
| Desktop | felt-tray (hotkeys, mic, watcher, tray) | `LaunchFelt.ps1` → `felt-tray.exe` |
| Desktop | Ollama (felt-animation's reaction picker) | scheduled task `OllamaServe` |
| Desktop | Rhubarb (lipsync) | external exe via `FELT_RHUBARB_EXE` |
| Desktop | LibreHardwareMonitor (GPU temp, WP-17) | separate app, must run **elevated** |
| Desktop | felt-dashboard (Vite/React) | dev tooling (pnpm, node_modules) |
| Desktop | rebuild/deploy | `UpdateFelt.ps1` (blanket commit+push), manual Godot export |
| Nitro5 | felt-voice (Chatterbox-Turbo + RVC Teto, STT) | systemd `felt-voice.service` (`uv run`) |
| Nitro5 | Ollama (router `qwen2.5:1.5b` on CPU, local chat `qwen2.5:3b`) | systemd |
| Nitro5 | ComfyUI (asset generation, WP-33) | user unit `felt-comfyui` |
| Nitro5 | models: Chatterbox weights, Teto RVC `.pth`/`.index`, reference clip, rmvpe, Whisper, Piper voices | hand-placed in `~/felt-voice/models`, the HF cache, etc. |
| Server | felt-core | clockmost-infra compose + sops `secrets.env`, vendored `app/`, deploy loop |

**Goal per device:**
- **Desktop:** one installer puts on **one app, "Felt"**, with **one tray
  icon**. That one process supervises everything else: no console windows
  flashing, no helper PowerShell, no scheduled-task tricks, no dev
  toolchain needed.
- **Nitro5:** one install command or package that sets up felt-voice plus
  Ollama (plus ComfyUI, optionally), with all models fetched and checked by
  manifest.
- **Server:** felt-core stays a clockmost-infra project. A fresh
  environment gets a documented bootstrap, not tribal knowledge.
- **All three:** a single `FRESH-INSTALL.md` that takes a wiped machine to
  a working Felt.

**Do (desktop, 34a):**
- **Host process:** felt-tray becomes the supervisor (or a small new
  launcher does). It:
  - starts felt-animation and the overlay as children with no windows
    (`CREATE_NO_WINDOW` / `pythonw`-style);
  - health-checks them and restarts on crash with backoff;
  - stops everything cleanly on quit;
  - shows each component's status (plus the Nitro5 and server
    reachability) in the tray menu and the status line;
  - owns single-instance locking, which avoids the duplicate-instance
    class of bugs.
- **Fold the helpers in:**
  - Move the click-through patch into native code (the supervisor via
    ctypes, or a tiny GDExtension), so there's no PowerShell.
  - Bundle Rhubarb.
  - Delete felt-vision if it's confirmed unused.
  - Replace LibreHardwareMonitor with an **unelevated** GPU temperature
    source (AMD ADLX or D3DKMT). If none works without elevation, say so
    and make it an optional feature.
- **Desktop Ollama:** find out what still uses it (felt-animation's
  reaction picker). Then either ship the Ollama runtime inside the bundle
  (started by the supervisor, with the model pulled on first run) or
  replace that use. No separate `OllamaServe` task.
- **One Python runtime, packaged:** PyInstaller or Nuitka, or an embedded
  CPython plus the app wheels, for felt-tray and felt-animation together.
- **Overlay:** the Godot template exe plus `.pck` (see the SAC note below),
  shipped inside the app folder.
- **Config:**
  - One `%APPDATA%\Felt\config.toml` replaces the per-repo `.env` files.
    It holds non-secret settings such as the server and voice URLs and the
    hotkeys.
  - Logs go to one `%LOCALAPPDATA%\Felt\logs\` folder.
  - A first-run screen asks for the server and Nitro5 addresses, or finds
    them.
- **Install, autostart, update:**
  - One installer (Inno Setup, MSIX, or a winget manifest) with a Start
    menu entry and autostart at login.
  - Uninstall removes everything except user data.
  - Self-update from the Gitea releases of a `felt-desktop` repo, with
    rollback to the previous build.
- **Dev mode keeps working:** running from the repos (`uv run …`) and
  exporting Godot for development stays possible. `LaunchFelt.ps1` /
  `UpdateFelt.ps1` retire once the bundle is the daily driver.

**⚠ Blocker to settle first: Smart App Control.** SAC is **on** on this
desktop and already blocks freshly built unsigned exes. That forced the
separate `.pck` export (c9ba3a0). A PyInstaller/Nuitka exe or a custom
launcher will be blocked the same way. The options have real trade-offs,
so this is **Mario's first decision** in this WP:
1. **Code-sign** the app (e.g. Azure Trusted Signing, a paid monthly
   service). This is the clean route.
2. **Keep every executable a signed stock binary**: the python.org
   `python.exe` / `pythonw.exe` running our code as a zip app, plus the
   official Godot template exe. This is what works today. The "single
   exe" is then a signed stub plus app files.
3. **Turn SAC off.** Windows doesn't let you turn it back on without a
   reset.

Research the current SAC rules before proposing any of these.

**Do (Nitro5, 34b):**
- Check the distro first. If it's Arch-based, package felt-voice as an Arch
  package through the existing `git.clockmost.com/pkgs` pipeline
  (`clockmost-package` skill), with its systemd units. Otherwise use a
  single idempotent install script.
- **A model manifest** (name, source URL, SHA-256, target path): Chatterbox
  weights, the Teto RVC model and index, the reference clip, rmvpe, the
  Whisper model, and Piper as the fallback voice. It is fetched on install
  and checked on start. Keep `FELT_VOICE_HF_OFFLINE` on after that.
- **Ollama:** the models (`qwen2.5:1.5b` router on CPU, `qwen2.5:3b` chat
  at ctx 4096) are pulled by the installer. The VRAM layout decided on
  2026-09-25 is written down as config, not tribal knowledge.
- **ComfyUI:** an optional component (WP-33 asset work), not part of the
  core install.

**Do (server, 34c):**
- felt-core already deploys through clockmost-infra. Make a fresh
  bootstrap explicit:
  - the required sops keys listed, without their values;
  - the first-run DB migration;
  - the health check;
  - how the vendored `app/` gets populated.

  Fix the CRLF archive gotcha permanently (`.gitattributes` or the deploy
  step).
- Write `FRESH-INSTALL.md` covering all three devices, in order, with a
  final "everything is green" check. The desktop tray status line showing
  all components green counts as that check.

**Accept:**
- **Desktop:** on a fresh Windows user account, one installer gives a
  working Felt after login:
  - one tray icon;
  - no console windows and no extra PowerShell or scheduled tasks;
  - SAC doesn't block anything.
- **Resilience:** killing felt-animation or the overlay recovers
  automatically. Quitting from the tray leaves no stray processes.
- **Nitro5:** a wiped machine is brought back by the documented install,
  with models verified by checksum, and `/v1/tts` answers in her voice.
- **Server:** felt-core is brought up from the infra repo following the
  runbook, with nothing undocumented.
- **Mario** follows `FRESH-INSTALL.md` (or reads it through) and judges
  it: "just the necessary stuff".
