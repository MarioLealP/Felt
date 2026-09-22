# WP-09 — Speech bubble, call ducking, "shut up" hush

**Repos**: `E:\Felt\felt-animation`, `E:\Felt\felt-character-assets`
(main.gd), `E:\Felt\felt-core` (small, deploy). **Size**: M. **Depends
on**: WP-08.

## Why (Mario's decisions, 2026-09-22)

Mario is on Discord calls most of the day. His words: "Bubble sure … it's a
lot of silence, I suppose it's also fine if she yaps while people are
speaking as long as she is quieter and I can always just tell her to shut up
if needed." So:
- **Every reply/reaction shows a speech bubble *and* is spoken immediately.**
  Nothing is queued or held back.
- **While someone on a call is talking, her voice is ~9 dB quieter.**
- **"Shut up"** cuts her off and starts a **10 min hush** where unprompted
  reactions are bubble-only. It's Mario-initiated, so it doesn't break the
  never-quiet rule.

## Changes

### 1. Speech bubble (main.gd + felt-animation)
- New relay message `{"bubble": {"text": "...", "seconds": 6.0}}`, and
  `{"bubble": null}` to clear.
- In main.gd: a 2D `CanvasLayer` → `PanelContainer` (rounded `StyleBoxFlat`,
  light background, dark text, 16–18 px, max width ~380 px, word-wrap) +
  a small tail triangle. Each frame, position it above her head: project the
  head bone's global position (`Skeleton3D.get_bone_global_pose` of
  `J_Bip_C_Head` / humanoid `head`, times the skeleton's global transform)
  with `camera.unproject_position`, offset upward, and clamp inside the window.
  Fade in 0.15 s; fade out at the end. While audio plays, stay visible until
  audio ends + 1.5 s, or `seconds`, whichever is longer. Long text: cap at ~3
  wrapped lines, ellipsise the rest (the full text is in the toast/chat).
- **Theme**: keep it neutral for now (Mario's broader design language is the
  Arknights Endfield aesthetic; a themed bubble can come later). Make colours
  and font constants at the top of the file.
- felt-animation sends the bubble in `_handle_reply` at the same synchronized
  start as audio (WP-08), for prompted and unprompted replies alike.
- Document the message in `felt-character-assets/README.md`.

### 2. Call ducking (felt-animation, `call_monitor.py`)
- `uv add pycaw comtypes`. A background thread polls every 50 ms:
  `AudioUtilities.GetAllSessions()`, and for sessions whose process name is
  in `FELT_CALL_APPS` (default
  `discord.exe,discordptb.exe,discordcanary.exe,ms-teams.exe,teams.exe,zoom.exe`)
  reads the peak via the session's `IAudioMeterInformation.GetPeakValue()`.
  Get it with `session._ctl.QueryInterface(IAudioMeterInformation)`; verify
  the exact pycaw incantation against its current docs.
- `talking = peak > FELT_CALL_PEAK_THRESHOLD (default 0.02)`, with **1.0 s
  hang time** after the last loud sample. Initialise COM per thread
  (`comtypes.CoInitialize()`).
- The gain target is `10 ** (-FELT_DUCK_DB / 20)` with `FELT_DUCK_DB` default
  **9** while `talking`, else 1.0. Push it to `audio.set_gain()` (which
  ramps). Log transitions at DEBUG.
- Expose `GET /status` → `{"call_talking": bool, "gain": float,
  "hush_until": iso|null, "playing": bool}`. WP-10's tray reads it.
- **Calibrate**: log the Discord peak distribution for a minute of silence
  versus talking during a real call (ask Mario to be on one), then set the
  threshold. Record the values in the notes.

### 3. Hush (felt-animation + felt-core)
- felt-animation `POST /hush?minutes=10`:
  - calls `/stop` (WP-08);
  - sets `hush_until`;
  - a repeat call extends it (+10 min, max 60);
  - `POST /unhush` clears it.
- During hush, `_handle_reply` with `prompted=0` → **bubble + face + body
  only, no audio** (skip `player.start` and the lipsync). `prompted=1` (Mario
  talked to her) speaks normally.
- **Voice/text command**: in felt-core, add a tiny skill
  `plugins/felt_presence/` with intents `shut_up` ("shut up", "shh", "be
  quiet", "quiet please", "stop talking") and `unhush` ("you can talk
  again", "ok talk"). It returns `SkillResult(text=<a short sheepish line,
  e.g. "okay okay, I'll zip it">, ui_action=UIAction(kind="presence",
  payload={"action": "hush", "minutes": 10}))`.
  - Add a router worked example and a deterministic regex fast path for
    these phrases.
  - `skills.json` class: `public` (WP-06).
  - felt-tray: on `ui_action.kind == "presence"`, call felt-animation
    (`/hush` or `/unhush`).
  - WP-10 extends this skill with the other presence actions.

## Tests
- felt-animation:
  - `call_monitor` decision logic as a pure function over a sample sequence
    (threshold + hang);
  - gain math;
  - hush state machine (extend, cap, expire);
  - `_handle_reply` during hush with `prompted=0` → no `player.start`, bubble
    sent;
  - `prompted=1` → speaks.
- felt-core: the presence skill regex and result shape.

## Acceptance
1. Every reply shows a bubble above her head that follows her when she walks,
   synced with the voice start.
2. On a real Discord call (Mario), her voice dips while a friend talks and
   comes back in silence, with no clicks. Threshold calibrated and recorded.
3. Saying "shut up" via the voice hotkey: she stops, says her short line, and
   the next screen reaction within 10 min is bubble-only. "You can talk
   again" restores speech. `GET /status` reflects all of it.
