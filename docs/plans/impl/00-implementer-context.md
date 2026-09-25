# 00 — Implementer context (read this before ANY work package)

You're implementing one work package (WP) from this folder for **Felt**,
Mario's desktop AI companion: a VRM anime avatar overlaid on his Windows
desktop that talks (her own voice), animates, and reacts to what's happening
on his screen. The design rationale for everything lives in
`E:\Felt\docs\plans\felt-review-2026-09-22.md` (the "review doc"). **The WP
file is your spec.** The review doc explains *why*. If they disagree, the WP
wins. If the WP is ambiguous, pick the option most consistent with the
standing rules below, and write down what you chose in the WP's "Notes from
implementation" section.

## Ground rules

1. **Do exactly one WP per session.** Don't start the next one, and don't
   "improve" neighbouring code that isn't in the WP. Other WPs will touch it.
2. **Verify for real.** Run the tests, hit the endpoint, check the log. Never
   report something works because the code looks right. Earlier agents on this
   project repeatedly claimed features were "fully wired" when they weren't
   deployed or silently failed. Mario checks.
3. **When done**: tick the WP in `README.md`'s status table, add a short
   "Notes from implementation" section at the bottom of the WP (what you did,
   deviations, anything left), and commit (see Git below).
4. **If blocked** on something only Mario can do (a login, a listen test, a
   judgement call), stop and say exactly what you need. Don't guess around
   it.

## Standing rules from Mario (non-negotiable)

- **Reaction-first.** Felt's main job is reacting to what's happening (screen,
  games, music, time); Mario is usually on a Discord call and doesn't want to
  talk to her. Reactions > conversation features.
- **Never truly quiet.** No automatic mute modes, and no LLM deciding to stay
  silent. Screen reactions are always spoken. How often she speaks is limited
  by deterministic rules (cooldowns, dedupe, budgets). While call audio is
  active, her voice is **ducked** (quieter), never held back. A "shut up" /
  hush that *Mario* triggers is fine.
- **One voice.** Every sound she makes ends in the Kasane Teto RVC model
  (felt-voice on the Nitro5). Since 2026-09-25 the base TTS is
  Chatterbox-Turbo, with Piper as the automatic fallback. RVC runs on the
  GPU. Whatever the base model, the output must end in the Teto voice: no
  other voices, and no Gemini Live API.
- **No uncurated non-verbals live.** felt-voice strips every paralinguistic
  tag (`[laugh]`, `[sigh]`, …). `FELT_VOICE_ALLOW_TAGS` is only for offline
  batches that Mario curates by ear. Laugh and chuckle are banned outright
  ("horrendous", 2026-09-25).
- **Screen-capture blocklist** (enforced by process/window *before* any
  pixels are grabbed, never by prompting a model): **Discord, all web
  browsers, File Explorer, WhatsApp, Telegram, Phone Link**, plus KeePassXC and
  banking. If nothing allowed is visible, there's no screen reaction.
- **Cloud privacy line.** Fetching data always happens locally. Result *text*
  may go to Gemini/Gemma to be phrased. Email, calendar, alarms, shopping list
  and music are fine for the cloud. Documents/Obsidian, remembered facts and
  phone location are never sent. Anything else goes through the local
  privacy classifier first.
- **Gemini is the free tier.** Every cloud call is counted and capped (see
  WP-05). High-volume work goes to **Gemma 4** (14.4K requests/day);
  conversation goes to **Gemini 3.5 Flash Lite** (500/day); **3.1 Flash Lite**
  (500/day) is overflow.
- **Godot is presentation only.** Decisions (what to play, when, why) live in
  felt-animation (Python) or felt-core. Godot blends, plays, moves and renders
  what it's told.
- **Avatar size is fixed** at `VERTICAL_MARGIN := 2.667` in main.gd. Never
  shrink her (tested: the mouth stops rendering).
- **Never suggest or use Mixamo.** Animation sources: the owned Movement
  Animset Pro (208 clips already converted in `E:\Felt\AnimToVrmaConverter\`),
  Quaternius UAL (CC0), the VRoid official VRMA pack, Booth, the Bandai Namco
  dataset, and felt-t2a-studio.
- **The Nitro5 isn't production.** Stopping/starting/swapping Ollama and ComfyUI
  there is fine. Its login shell is **fish**: wrap bash syntax as
  `ssh clockmost-nitro5 "bash -c '…'"`.
- **Python = `uv`** everywhere (`uv add`, `uv sync`, `uv run`). No pip.
- **No hardcoded secrets or addresses.** Config comes from `.env` / env vars
  (every repo has a `config.py` + `.env.example`; update both when adding a
  setting).

## Machines and layout

| What | Where |
|---|---|
| Desktop (Windows 11, AMD RX 6700, 3440×1440 primary + 1920×1080 at x=3440,y=357) | this machine. Felt's local pieces run here. |
| Felt umbrella | `E:\Felt\` (git repo for docs/scripts). Each component is its own git repo inside it (gitignored by the umbrella). `F:\workspace\Projects\<repo>` are **junctions** to these, same files. |
| felt-core (brain/API) | code `E:\Felt\felt-core`; **runs on the server** `clockmost` (192.168.1.110:8420) in Docker. |
| felt-animation (behaviour, lipsync, drives the overlay) | `E:\Felt\felt-animation`, desktop, port 8421. |
| felt-tray (hotkeys, mic, tray, watcher, playback) | `E:\Felt\felt-tray`, desktop. |
| felt-vision (local llava describer) | `E:\Felt\felt-vision`, desktop, port 8080. Being superseded by WP-06. |
| Godot overlay (the avatar) | `E:\Felt\felt-character-assets\felt-godot-overlay\` (`main.gd`), exported to `build\windows\FeltOverlay.exe`. |
| Animation library | `E:\Felt\Animations` (junction). Folder path = tag, e.g. `emotion/happy/*.vrma`. |
| felt-voice (STT + TTS + RVC) | Nitro5 laptop `ssh clockmost-nitro5` (192.168.1.104), `felt-voice.service`. |
| Ollama for felt-core | Nitro5 `:11434` (router/privacy `qwen2.5:1.5b`, local chat `qwen2.5:3b` at `num_ctx` 4096 since 2026-09-25, downsized so the 6 GB GPU fits the voice stack; the router runs on CPU). |
| Ollama for desktop pieces | desktop `127.0.0.1:11434`. |

**Message flow today**: hotkey → felt-tray records → `POST felt-core
/v1/voice-chat` → reply WAV + `X-Reply-Text` / `X-Animation-Tag` headers →
felt-tray plays the WAV and `POST felt-animation /reply_ready` (text, tag,
audio) → felt-animation runs Rhubarb lipsync + picks a reaction → TCP JSON lines
to the overlay on `127.0.0.1:8765`. Screen: window switch → felt-tray
`watcher.py` screenshot → felt-vision `/analyze` → `felt-core
/v1/context/screen`.

**Overlay relay protocol** (newline-delimited JSON to TCP 8765, handled in
`main.gd` `_handle_tag_line`):
- `{"tag": "emotion/happy"}` plays a random clip in that tag folder.
- `{"move": {"x": 1.2}}` sets the horizontal target.
- `{"lipsync": [{"start", "end", "value"}, …]}` starts the mouth timeline on
  receipt.
- `{"expression": {shape_or_preset: weight}}`.

The overlay sends back `{"finished": "<tag>"}` when a one-shot clip ends. WPs
extend this protocol. Keep it additive and document new messages in
`felt-character-assets/README.md`.

## Running, building, deploying

- **Launch everything**: `E:\Felt\LaunchFelt.ps1` (Desktop shortcut "Launch
  Felt"). Starts felt-animation (which launches the overlay), felt-vision and
  felt-tray, all hidden.
- **Rebuild the overlay after changing main.gd**: `E:\Felt\UpdateFelt.ps1`.
  Note that it also commits+pushes felt-character-assets. If you don't want
  that, export directly:
  `E:\Felt\felt-character-assets\tools\godot\Godot.exe --headless
  --export-release "Windows Desktop" build/windows/FeltOverlay.exe` (run in
  `felt-godot-overlay`), then restart felt-animation (kill the `python.exe`
  whose command line contains `felt_animation`, then start
  `E:\Felt\felt-animation\.venv\Scripts\python.exe -m felt_animation`
  hidden).
- **Logs**: felt-tray → `%TEMP%\felt-tray.log`. felt-animation and
  felt-vision log to the console only, and they run hidden, so run them in
  the foreground to see output until WP-01 adds file logs.
- **felt-core tests**: `cd E:\Felt\felt-core; uv run pytest -q` (135 passing
  at baseline; must stay green).
- **Deploying felt-core** (the server runs a *vendored copy*; pushing
  felt-core's own repo does NOT deploy it):
  1. Commit and push in `E:\Felt\felt-core`.
  2. Copy the tree to the server's vendored copy:
     `git -C E:/Felt/felt-core archive HEAD | ssh clockmost-claude "tar -x -C /home/clockmost-infra/projects/felt-core/app"`
     (or `scp` individual changed files into
     `/home/clockmost-infra/projects/felt-core/app/...`).
  3. On the server, in `/home/clockmost-infra`: `git add
     projects/felt-core/app && git commit -m "felt-core: <what>" && git push`
     (its origin is the local Gitea). **You must push**: the deploy loop
     resets to origin and would otherwise revert you.
  4. Trigger the deploy: `ssh clockmost-claude "sudo -n -v 2>/dev/null; sleep 1; sudo -n systemctl start clockmost-deploy.service"`,
     then watch it with `ssh clockmost-claude "sudo -n journalctl -u clockmost-deploy.service -n 30 --no-pager"`.
     Look for `deployed felt-core`; it auto-reverts on a failed health
     check.
  5. Verify live: `curl` the changed endpoint at `http://192.168.1.110:8420`,
     and read `docker compose logs -t --since 5m felt-core` in
     `/home/clockmost-infra/projects/felt-core`.
  - Secrets (Gemini key, etc.) are in that project's sops `secrets.env`. Don't
    print or commit them. New *non-secret* settings go in felt-core's
    `config.py` with defaults plus `.env.example`.
  - The auto-mode permission classifier blocks direct reads of the production
    SQLite DB. Verify through the API and logs instead, and don't try to work
    around it.

## Git

- Each repo commits and pushes to `git.clockmost.com` over SSH (remotes are
  already set). Conventional, descriptive commit messages. In bash, **don't
  put backticks inside double-quoted `-m` strings** (command substitution eats
  them). Use a heredoc or single quotes.
- Never commit `.env`, secrets, or `AnimToVrmaConverter`'s paid
  `Movement Animset Pro*.unitypackage`.
- The umbrella repo `E:\Felt` holds docs and scripts. Commit WP status updates
  there.

## Known gotchas (each one has already cost real time)

- `winsound` can't play from memory asynchronously. Playback uses a temp file
  (`felt-tray/src/felt_tray/playback.py`).
- In Godot, never call `window_set_mode(MINIMIZED)` before size/position are
  set: they silently don't stick.
- The overlay's full-window transparency plus spanning both monitors crashed
  the AMD Vulkan driver. It's why the overlay is primary-only and on the
  `gl_compatibility` renderer. WP-22 solves multi-monitor with a small
  follow-window instead.
- VRM face shapes are VRoid names (`Fcl_ALL_Joy`, `Fcl_EYE_Close_L`,
  `Fcl_MTH_A`…) plus VRM presets (`happy`, `aa`…). The full list of 57 is in
  review doc §F.
- `library.scan_tags()`: a folder is a tag only if it *directly* contains
  `.vrma`/`.vrma.import` files. Never hardcode leaf tag names. Check
  `known_tags`, or prefix-scan with `_known_tags_under()`.
- felt-core can't know the desktop's animation tags. Any tag coming from the
  server must be validated and broadened on the desktop (WP-01).
