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

## Notes from implementation (2026-09-23)

Implemented as specced, both sides. Commits: felt-tray `d6def22`, felt-core
`6fb79d3` (+ `d3a2768` for an unrelated concurrent Gemini commit swept up
along the way, see below) deployed via `/home/clockmost-infra` `aeb6956`
+ `clockmost-deploy.service` ("OK — deployed felt-core").

**Real Win32 validation before writing capture.py**: ran a live ctypes
enumeration + a real `windows_capture` single-window grab against this
actual desktop before committing to the design. Confirmed: `EnumWindows` +
`DwmGetWindowAttribute` (cloaked/extended-frame-bounds) +
`QueryFullProcessImageNameW` correctly identifies real windows (Discord,
Firefox, Spotify, WindowsTerminal, FeltOverlay, all with correct
process/pid/rect); `windows_capture`'s `window_hwnd` capture produces a
clean, correctly-cropped image of exactly that window (verified against
Firefox showing a real page, and Spotify - both test captures were
deleted immediately after confirming, per the same discipline the
capture pipeline itself is meant to enforce).

**WhatsApp/Phone Link/Telegram identification (WP's own required step)**:
confirmed live via `Get-Process` + `Get-AppxPackage`, 2026-09-22 - both
WhatsApp Desktop and Phone Link were already running on this machine.
**Contradicts the WP's own assumption**: neither is hosted via
`ApplicationFrameHost.exe` - both spawn their own direct process
(`WhatsApp.Root.exe`, `PhoneExperienceHost.exe`). The
`ApplicationFrameHost` child-window-traversal logic the WP describes
turned out to be unnecessary for these two apps' current versions (it's
a pattern from older-style UWP apps; the Settings app on this machine
uses it, confirming the mechanism is real, just not needed here).
Telegram isn't installed on this machine at all (no Store package, no
classic desktop install) - `telegram.exe` is in the blocklist as a
forward-looking default; Telegram Web is already covered by the browser
blocklist regardless.

**Deviation from the WP's exact function signature**: `cloud_generate`
already required an explicit `config` parameter (a WP-05 decision, not
in that WP's own signature sketch either) - `react_to_screen` follows
that same established convention.

**Live acceptance, verified 2026-09-23 ~09:47-09:49 (session
`dashboard`, ~4 minute window, `FELT_SCREEN_SAMPLE_S` temporarily set to
20s to compress the test - reverted to the 45s default afterward)**:
1. Discord and Firefox were open and visible the ENTIRE test window
   alongside an allowed app (WindowsTerminal) - every one of the 7 saved
   debug JPEGs is `windowsterminal_exe`, never Discord or Firefox. The
   exact "everything blocked -> skip, nothing sent" case is also directly
   unit-tested (`test_all_blocked_returns_none`), not separately
   reproduced live (would have meant minimizing Mario's actual open
   windows to force it).
2. An allowed window (WindowsTerminal, running this very session) got a
   real, relevant, in-character reply: "Looks like things are getting a
   bit technical in here, huh?" (emotion=amused) for one capture, "Looks
   like things are moving along in the background. Keep it up!"
   (emotion=amused) for another - both genuinely responsive to what was
   actually on screen. Debug JPEG confirmed a clean, correctly-cropped
   capture of just that window (verified visually, then left in place
   under `FELT_CAPTURE_DEBUG_DIR` for Mario's own check 5 sign-off).
3. Periodic samples fired every ~20-40s (dedup/timing jitter) for the
   full window; exactly 2 real spoken reactions happened in ~4 minutes
   (09:47:19 and 09:49:12 - 113s apart, correctly over the 90s cooldown),
   every capture in between returned `reply=''` (cooldown correctly
   suppressing the model call server-side, not the client withholding
   the send).
4. `/v1/metrics/cloud` usage: `{"model": "gemma-4-26b-a4b-it", "purpose":
   "screen_reaction", "count": 2}` - matches the 2 real spoken reactions
   exactly.
5. **Needs Mario**: `F:\Temp\felt-capture-debug\` has 7 real JPEGs from
   this test run, ready for his sign-off glance. `FELT_CAPTURE_DEBUG_DIR`
   is still set in `felt-tray/.env` - **someone needs to unset it after
   he's looked**, per the WP's own explicit step. Felt was left stopped
   after testing (his own stated preference this session).

**Real, unrelated hiccup along the way**: right after `uv add
windows-capture` (which pulled in `opencv-python`), the very next
`imagehash.phash()` call failed with `ImportError: DLL load failed ...
An Application Control policy has blocked this file` (scipy's
`cython_lapack`, a pre-existing transitive dependency of `imagehash`,
not anything newly added). Self-resolved on the very next Python
process start - consistent with a one-time Windows Defender/Smart App
Control reputation check on a freshly-touched `.venv`, not a real,
persistent blocker. Not investigated further since it didn't recur;
worth remembering if it resurfaces after a future `uv add` in this repo.

**Concurrent Gemini work, same pattern as earlier this session**:
`plugins/skills.json` and `plugins/tags.json` had picked up a
`change_shirt` entry from a concurrent Antigravity/Gemini session
between when this WP's `skills.json` was written and committed, plus a
whole new (not yet wired up - no `skill.py`) `plugins/change_shirt/`
scaffold. The scaffold + tags.json entry went into their own `[gemini-wip]`
commit (`d3a2768`); the one-line `skills.json` addition rode along in
this WP's own commit with a note, rather than fighting to hunk-split a
single low-risk JSON entry out of a file this WP already owns - per
Mario's own standing guidance on handling this pattern.
