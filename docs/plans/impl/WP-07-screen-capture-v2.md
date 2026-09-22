# WP-07 — Screen capture v2: per-window capture + blocklist + Gemma vision reactions

**Repos**: `E:\Felt\felt-tray` (watcher), `E:\Felt\felt-core` (new endpoint,
deploy). **Size**: L. **Depends on**: WP-05 (cloud governor). WP-02 must be
in too (observations table, cooldown).

## Why

Reacting to what Mario is doing is Felt's #1 job. Today:
- `felt-tray/src/felt_tray/watcher.py` fires **only on foreground-window
  changes**. Hours in one game give zero reactions.
- It grabs the **whole primary monitor**, Felt herself and private apps
  included.
- It relies on a llava prompt ("don't transcribe private stuff") as the
  privacy guard, and llava-7B is weak at game screens.

## Mario's rules (decided, don't relitigate)

- **Blocklist, enforced before any pixels are grabbed**: Discord, every web
  browser (chrome, msedge, firefox, brave, opera, opera_gx, vivaldi, arc,
  zen…), File Explorer (explorer.exe windows of class `CabinetWClass`),
  WhatsApp, Telegram, Phone Link, KeePassXC, plus banking by title regex.
- If nothing allowed is visible, there's no screen reaction.
- Reactions are spoken (the WP-02 prompt), with a deterministic cooldown.
- Discord's in-game overlay is off, and Steam DMs aren't a concern.

## Design: capture one *window*, not a screen

### Desktop side (felt-tray), new module `capture.py` + reworked `watcher.py`
1. **Enumerate** visible top-level windows on both monitors: `EnumWindows`;
   skip invisible, minimized, cloaked (`DwmGetWindowAttribute(DWMWA_CLOAKED=14)`),
   `WS_EX_TOOLWINDOW`, and tiny windows. Get the rect via
   `DWMWA_EXTENDED_FRAME_BOUNDS (9)`. Call
   `SetProcessDpiAwarenessContext(-4)` once, at startup. A working ctypes
   prototype of exactly this enumeration was run on this machine; reuse the
   approach.
2. **Identify the app** for each window: `GetWindowThreadProcessId` → process
   image name (`QueryFullProcessImageNameW`). **Packaged/Store apps**
   (WhatsApp, Phone Link, possibly Telegram): if the process is
   `ApplicationFrameHost.exe`, find the hosted child window's process
   (`EnumChildWindows`, class `Windows.UI.Core.CoreWindow`). Also read the
   package family name when available (`GetApplicationUserModelId` /
   `GetPackageFamilyName` on the process). **Before finalising the
   blocklist, run a one-off script with WhatsApp, Telegram and Phone Link
   open, and record their real process names and package family names in
   this WP's notes.**
3. **Blocklist config**: `felt-tray/capture_blocklist.toml`, versioned (it's
   Mario's policy, not a secret):
   ```toml
   processes = ["discord.exe", "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "opera_gx.exe", "vivaldi.exe", "arc.exe", "zen.exe", "whatsapp.exe", "telegram.exe", "phoneexperiencehost.exe", "keepassxc.exe", "explorer.exe"]
   package_families = []   # fill from step 2 (WhatsApp / Phone Link / Telegram Store)
   window_classes = ["CabinetWClass"]     # File Explorer
   title_regexes = ["(?i)\\b(bank|banco|caixa|millennium|revolut|paypal|mbway)\\b"]
   ```
   Match case-insensitively. **If a window can't be identified, treat it as
   blocked** (fail closed).
4. **Target selection**: the focused window if allowed; else the largest
   visible allowed window that is fullscreen or borderless-fullscreen; else
   the largest visible allowed window. Also exclude FeltOverlay's own window
   and felt-tray's own windows. None → no capture, and log `skip: nothing
   allowed visible`.
5. **Capture only that window**: Windows Graphics Capture. Evaluate the
   `windows-capture` PyPI package (Rust-backed): confirm its current API for
   capturing by HWND/title, single-frame grab, and the Windows 11 option to
   hide the yellow capture border.
   - Fallback: `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` via ctypes.
   - If the frame is (near) all-black, skip. Some DirectX games do that with
     PrintWindow. **Never** fall back to a full-screen grab.
   - Downscale to 768 px on the long side, JPEG q80.
6. **Triggers**:
   - Foreground change, debounced 3 s (alt-tab bursts settle).
   - A periodic sample every `FELT_SCREEN_SAMPLE_S` (default **45**) while
     the same allowed window stays in front.
   - Dedupe: keep the last-sent phash per window key (process + title); skip
     if the phash distance is ≤ 6 (tune it; log the distances for the first
     day).
   - Hook for WP-10: skip while Felt is hidden or away (read a shared state
     flag; stub it as always-visible for now).
7. **Send** `POST {felt_core_url}/v1/react/screen` as multipart: `image` (the
   JPEG), `app` (exe name), `title` (window title), `trigger`
   (`focus|periodic|manual`). Then handle the response exactly like today's
   `_on_screen_context` (toast, audio, `reply_ready`).
8. **Debug aid**: if `FELT_CAPTURE_DEBUG_DIR` is set, save every JPEG that
   was *sent*, with a timestamp and app name, so Mario/you can verify only
   the right window leaves the machine. Off by default.
9. Retire felt-vision from the default path. Keep it as a fallback: if
   `/v1/react/screen` returns **503 `cloud_unavailable`**, send the same JPEG
   to felt-vision `/analyze` and post the description to the existing
   `/v1/context/screen`.

### Server side (felt-core): `POST /v1/react/screen`
- Accept multipart (`image`, `app`, `title`, `trigger`, `session_id`
  default `"dashboard"`).
- Apply the WP-02 cooldown **before** calling any model. `trigger=manual`
  (WP-10's "look at this" key) bypasses it.
- **One** call:
  `cloud_generate("screen_reaction", system=personality (+ tone line later),
  messages=[observations block (last 3) + "App: <app> — '<title>'" +
  instruction], images=[jpeg], json_mode=True)`. Expected JSON:
  `{"seen": "<one short neutral sentence of what's on screen>", "line": "<her
  spoken remark, ≤ ~15 words, in character, never mentions screens or
  screenshots>", "emotion": "happy|excited|amused|sad|annoyed|surprised|thinking|sleepy|neutral"}`.
- Save `seen` as the observation description (WP-02 table), and the `line`
  as spoken reply + assistant message. Return the same response shape as
  `/v1/context/screen`, plus an `X-Emotion` header (add it to CORS
  `expose_headers`).
- `CloudUnavailable` → `503 {"detail": "cloud_unavailable"}` (the watcher
  falls back as above). **Images never go to the local Ollama on the
  server**, since there's no local VLM there.
- JSON parse failure → retry once without json_mode, instructing "only
  JSON"; then give up (no reaction, WARNING log).

## Tests
- felt-tray `tests/test_capture_policy.py`: pure functions for blocklist
  matching and target selection, over fake window lists (focused-blocked
  plus allowed-other → other; all blocked → None; unknown process → blocked).
  Rule for Explorer: **every `explorer.exe`-owned window is blocked** (File
  Explorer, desktop, taskbar; none are worth reacting to), so add
  `explorer.exe` to `processes`. The `CabinetWClass` entry is just belt and
  braces.
- felt-core `test_react_screen.py`: cooldown, manual bypass, the JSON contract,
  the 503 path, and that the image reaches `cloud_generate` (fake it).

## Acceptance
1. With Discord focused and a browser on the other screen, both visible:
   the log says `skip: nothing allowed visible`, and nothing is sent.
2. Open any allowed app (Notepad or a game) next to Discord: exactly that
   window's image is sent (check `FELT_CAPTURE_DEBUG_DIR`), and she speaks a
   relevant line.
3. Stay in a game (or a video player) for 3 minutes: periodic samples appear
   in the log, unchanged frames are skipped by the phash, and reactions
   respect the 90 s cooldown.
4. `/v1/metrics/cloud` shows `screen_reaction` counts on the Gemma model.
5. Ask Mario to glance at the debug JPEGs once. That's the privacy sign-off.
   Then unset `FELT_CAPTURE_DEBUG_DIR`.
