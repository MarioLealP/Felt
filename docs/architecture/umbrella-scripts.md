# Umbrella Scripts & Tools

## Purpose

E:\Felt top-level orchestration: launcher scripts, update/export pipeline, Nitro5 service checks, plus asset tools (outfits, sounds, llamacpp binaries, review utilities).

## Runtime

**Desktop launchers (Windows 11 shortcuts):**
- Launch Felt.bat → LaunchFelt.ps1 (starts Ollama, felt-animation, felt-vision, felt-tray)
- Update Felt.bat → UpdateFelt.ps1 (Godot export, asset commit, felt-animation restart)
- Start Nitro5.bat → StartNitro5.ps1 (SSH checks, starts felt-voice/ollama on Nitro5 if down)

**Execution:** PowerShell 5.1 (Windows built-in), no uv/python; .bat files use `powershell.exe -ExecutionPolicy Bypass`

**SSH:** All Nitro5 commands via `ssh clockmost-nitro5` (key-based auth, dedicated host alias)

## Module Map

| File | LOC | Responsibility |
|------|-----|---|
| LaunchFelt.ps1 | 52 | Ollama check/start (scheduled task), kill running instances, launch felt-animation/vision/tray |
| UpdateFelt.ps1 | 73 | Godot executable dialog, kill overlay, asset commit/push, Godot export, copy patch-clickthrough.ps1, restart felt-animation |
| StartNitro5.ps1 | 35 | SSH systemctl is-active checks, sudo -n start felt-voice/ollama if down |
| Launch Felt.bat | 2 | Wrapper: calls LaunchFelt.ps1 with Bypass policy |
| Update Felt.bat | 2 | Wrapper: calls UpdateFelt.ps1 |
| Start Nitro5.bat | 2 | Wrapper: calls StartNitro5.ps1 |
| **tools/** | **2002 total** | Asset pipelines (not launched by shortcuts, used manually/WP-specific) |
| tools/outfits/ | 937 | VRM outfit generation (generate_tees.py 303 LOC, regenerate_html.py 185, patch_main.py 136) |
| tools/sounds/ | 947 | Audio curation (build_curation_page.py 250, nitro/ batch jobs: wp19_audio.py 115, chatterbox_nonverbals.py 137) |
| tools/llamacpp/ | — | llama.cpp binaries (~20 DLLs/EXEs, ~500 MB) for local inference (not active in main Felt) |
| tools/review/ | — | (directory only observed, contents not listed) |

**docs/ structure:** E:\Felt\docs/plans/ contains workplan markdown (WP-01 through WP-36, audit logs, whitepapers) — not launcher-related.

## Interfaces

**LaunchFelt.ps1:**
- Checks `http://127.0.0.1:11434/api/tags` (Ollama readiness) with 2s timeout, 10 retry loop (lines 14-20)
- Kills python.exe running felt_animation/felt-tray/felt_vision (line 27: cmd-line match)
- Starts .venv\Scripts\python.exe with -m or -c flags (lines 33, 45, 49)
- No inter-process sync; each child runs independently

**UpdateFelt.ps1:**
- Reads E:\Felt\godot_path.txt; prompts file browser if missing (lines 1-21)
- Runs `git add -A` + commit + push in felt-character-assets (line 33, risky)
- Invokes Godot headless: `--headless --export-release "Windows Desktop" build/windows/FeltOverlay.exe`
- Copies patch-clickthrough.ps1 from source to build/ (line 62, hardcoded relative path)

**StartNitro5.ps1:**
- SSH: `systemctl is-active felt-voice.service ollama.service` (line 9, outputs two lines)
- SSH: `sudo -n systemctl start <service>` if inactive (lines 18, 28)
- No error recovery; warns "is ComfyUI using GPU?" if ollama fails (line 31)

## Config

**Hardcoded paths:**
- E:\Felt\godot_path.txt — user's Godot executable location (created on first run)
- E:\Felt\felt-character-assets — asset git repo (line 32, 45)
- E:\Felt\felt-animation — animation module (line 32, 65)
- E:\Felt\felt-vision — vision module (line 44)
- E:\Felt\felt-tray — tray module (line 48)

**SSH constants:**
- clockmost-nitro5 (resolved to 192.168.1.xxx by ~/.ssh/config)

**Env dependencies:**
- LaunchFelt checks/starts scheduled task "OllamaServe" (Windows Task Scheduler)
- StartNitro5 assumes scoped NOPASSWD sudo on Nitro5 for systemctl

## Tests

None. Manually tested via desktop shortcuts (latest: 2026-09-21 per comments).

## Smells

- **UpdateFelt.ps1 line 33: `git add -A`** — RISKY: commits all changes in felt-character-assets, no safelist; could include unintended files (e.g., .venv, temp build artifacts). Should be explicit file list or dry-run confirmation.
- **UpdateFelt.ps1 line 62: hardcoded relative path** — `Copy-Item "patch-clickthrough.ps1"` assumes pwd is felt-godot-overlay; Set-Location mitigates but no validation
- **LaunchFelt.ps1 line 27: process matching by name/cmdline** — kills python.exe if cmdline contains felt_animation/felt_vision/felt_tray; fragile (false positives if other python scripts running). Should use PID file or scoped executable name (felt-animation.exe if packaged)
- **No inter-process sequencing** — LaunchFelt starts felt-animation, felt-vision, felt-tray in rapid sequence without verification. If felt-vision slow to bind, felt-tray's first screen-capture might fail
- **StartNitro5.ps1 line 9: assumes two-line output** — `systemctl is-active` returns one status per service; script indexes $lines[0], $lines[1]. If output format changes (multiline error), parsing breaks
- **No .env files** — all paths hardcoded; can't easily run from a different directory
- **Ollama start waits only 10s** — LaunchFelt loop (line 14-20) gives Ollama max 10 retries × 1s sleep = ~10s; on slow disk, may timeout before Ollama ready
- **No logging** — all Write-Host output; can't grep/audit launch history. Suggestions to redirect to %TEMP%\LaunchFelt.log

## Ranked Suggestions

1. **Whitelist files in git add** (M, agent-ok) — UpdateFelt.ps1: replace `git add -A` with explicit paths (felt.vrm, Animations/, Model/, VRoid/) or `git add --intent-to-add` + review before commit
2. **Use PID file for process management** (M, no) — LaunchFelt/UpdateFelt: write PIDs to E:\Felt\.pids/felt-vision.pid, read them back instead of name/cmdline matching
3. **Add inter-process readiness checks** (M, agent-ok) — LaunchFelt: after starting felt-vision, wait for GET http://127.0.0.1:8080/health 200 before starting felt-tray
4. **Log to file** (S, agent-ok) — redirect all Write-Host to E:\Felt\.logs\LaunchFelt.log with timestamps for debugging launch failures
5. **Increase Ollama startup timeout** (S, agent-ok) — LaunchFelt line 14: raise loop count to 20 (20s total) or make configurable via env var OLLAMA_STARTUP_SEC
6. **Document SSH config** (S, agent-ok) — add comment explaining clockmost-nitro5 alias, scoped sudo requirement, expected host IP
7. **Validate Godot path existence** (S, agent-ok) — UpdateFelt.ps1: after reading/prompting godot_path.txt, verify file exists and is executable
