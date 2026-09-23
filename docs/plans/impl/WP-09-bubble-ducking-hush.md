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

## Notes from implementation (2026-09-23)

**Not done - needs Mario directly:**
- **Acceptance 2** (call-ducking calibration): `FELT_CALL_PEAK_THRESHOLD`
  defaults to 0.02 (the WP's own starting guess) and `FELT_DUCK_DB` to 9 -
  neither has been measured against a real Discord call with someone else
  actually talking, since that needs Mario present on one. `call_monitor.py`'s
  own docstring flags this. Once there's a real call to test against: watch
  `felt-animation.log` at DEBUG for `call talking=%s (peak=%.4f)` lines
  while a friend talks vs. silence, and set the threshold between the two
  observed peak ranges.
- The eye/ear halves of acceptance 1 and 3 (bubble tracking her head
  visually while she walks, actually hearing the duck with no clicks,
  judging the sheepish face) - same category as WP-08's own "Mario judges
  by eye" items, not something I can verify myself.

**What was built and verified without him:**

*felt-animation* - `overlay.bubble()`/`clear_bubble()` send the relay
message from `_handle_reply` at the same synchronized point as
lipsync/audio (WP-08's own "one synchronized start"), for both prompted
and unprompted replies. `call_monitor.py`: `TalkingDetector` (threshold +
1.0s hang time) and `duck_gain` are pure/unit-tested; the actual pycaw
polling thread isn't (needs real Windows audio sessions) - verified instead
by reading pycaw's actual installed source (`.venv/Lib/site-packages/pycaw/
utils.py`) to confirm the exact incantation the WP asked to verify:
`session._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()`,
`session.Process.name()` for the process filter. Found and fixed a real
interaction bug while building this: `AudioPlayer.start()` used to reset
gain to 1.0 on every new utterance, which would have snapped a call-ducked
voice back to full volume for ~50ms at the start of each reply during an
ongoing call until the next poll tick corrected it - gain now persists
across `start()` calls instead (test_gain_persists_across_a_new_start_for_call_ducking).
`hush.py`'s extend/cap/expire is clock-injected and fully unit-tested
(including the 60-minute cap actually engaging on repeated extension
calls). `_handle_reply`: `speak = prompted or not hush.active` - verified
both live (see below) and via `test_handle_reply_sync.py`'s three new
hush-path tests.

*felt-character-assets* - the bubble CanvasLayer/PanelContainer/Label/tail,
positioned every frame from the Head bone's projected screen position (via
`_main_cam.unproject_position`), alpha-faded (0.15s) rather than a state
machine. Verified two ways: a headless Godot load (`--quit-after 2`) that
ran cleanly through `_build_bubble_ui()` and all the way to "Tag listener
started" with no parse/runtime errors, and a live run against a real
felt-animation server actually sending bubble+lipsync message pairs
(including during hush) with the real overlay process staying responsive
throughout (checked via `Get-Process`, no crash). No visual confirmation
that the bubble actually tracks her head correctly on screen or reads well
- that's Mario's own look.

*felt-core* - `felt_presence` skill (shut_up/unhush intents ->
`UIAction(kind="presence", ...)`), `_presence_fast_path` regex in brain.py
(checked before `decide_tool` runs at all, so "shut up" never waits on or
risks a misroute from the router LLM), plus a router worked example as a
fallback for other phrasings. Along the way, found the `SkillResult.ui_action
-> X-UI-Action` header plumbing (pre-existing, used by no skill until this
one) had zero test coverage at all - added `test_ui_action_plumbing.py` to
close that gap generically, not just for this one skill.

*felt-tray* - `_handle_ui_action`, called from both `_finish_voice_chat`
and `_on_screen_reaction`, POSTs to felt-animation's `/hush`/`/unhush` on a
`kind: "presence"` result.

**Live end-to-end check** (felt-animation booted for real, same
`uv run python -m uvicorn` workaround as WP-08 for the occasional
Application-Control-blocked `uvicorn.exe` stub): sent a prompted reply
(spoke + bubbled), hushed for 10 min, sent an unprompted reply during hush
(logged `hushed - bubble/body only, no audio (prompted=False)`, no
`player.start` call, mouth stayed at rest), sent a prompted reply during
the same hush (spoke normally, `sync offset=16.0ms`), unhushed, then fired
nine back-to-back `/hush` calls to confirm the 60-minute cap actually
engages (the first six extended by a clean 10 minutes each; the 7th-9th
calls landed only seconds apart, exactly where the cap formula predicts).
`GET /status` reflected `call_talking`/`gain`/`hush_until`/`playing`
correctly throughout. Overlay process (`FeltOverlay.exe`) stayed alive and
responsive (`Get-Process` `Responding: True`) after all of it. Cleaned up
(stopped the test server + overlay, confirmed port 8421 free) afterward,
same discipline as WP-08.

Committed as four separate repo commits (felt-animation, felt-character-
assets, felt-core, felt-tray). No concurrent Gemini/Antigravity WIP was
found in any of the four repos when checked before starting (all `git
status` clean) - the `[gemini-wip]`-separation pattern from earlier WPs
wasn't needed this time. `tools/outfits/` in the umbrella repo has
unrelated uncommitted wardrobe-feature changes (not mine, not touched) -
left alone, only `docs/plans/impl/` staged for this commit.
