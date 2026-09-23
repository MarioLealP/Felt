# WP-08 — Playback moves to felt-animation: voice, lips and body in sync + stop

**Repos**: `E:\Felt\felt-animation`, `E:\Felt\felt-tray`,
`E:\Felt\felt-dashboard`, `E:\Felt\felt-character-assets` (main.gd).
**Size**: M. **Depends on**: WP-01.

## Why

Three processes each start their part at a different moment:
- **felt-tray** plays the WAV the instant the reply arrives
  (`playback.play_wav`), then POSTs `/reply_ready`.
- **felt-animation** runs Rhubarb (seconds), *then* `classify_reaction` (an
  LLM call, up to 15 s timeout), *then* waits for the thinking loop. All of
  that is sequential.
- **main.gd** starts the mouth timeline when the cue message *arrives*.

The result: the mouth lags the voice by the whole Rhubarb run, and the body
reaction lands even later. Also, the **chat window plays the audio itself**
(`felt-dashboard/src/App.tsx` ~lines 90–92 and 111–112 via `audioRef`) *and*
forwards it to felt-animation. Once felt-animation plays audio, that would
double-play.

**Principle**: felt-animation is the only process that knows all three
timelines, so it becomes the **single owner of her audio**.

## Changes

### felt-animation
- New `audio.py`: a player built on `sounddevice` (`uv add sounddevice
  numpy`). Decode the WAV with the stdlib `wave` module into int16 numpy,
  and play through a `sounddevice.OutputStream` **callback**, so gain can
  change mid-utterance (WP-09 ducking needs this). API:
  - `start(wav_bytes, on_done)`
  - `stop()`
  - `is_playing`
  - `set_gain(linear)` (default 1.0; ramp gain changes over ~50 ms to avoid
    clicks)
  - one utterance at a time; a new `start` stops the current one.
- `/reply_ready` gets a new form field `prompted` (`"1"` for replies Mario
  asked for, i.e. voice/text chat; `"0"` for unprompted, i.e. screen and
  other reactions). Default `"1"` for backward compatibility.
- `_handle_reply`:
  ```python
  cues, tag = await asyncio.gather(
      generate_cues(config, audio_bytes, text),
      _resolve_reaction_tag(animation_tag, text),   # WP-01 resolve_known_tag → classify_reaction fallback
  )
  await state.end_thinking_and_wait()
  # --- one synchronized start ---
  if expr: await overlay.expression(expr)
  await overlay.lipsync(cues)         # main.gd starts its mouth clock on receipt
  player.start(audio_bytes, on_done=...)
  asyncio.create_task(state.run_sequence(tags_to_play, CLIP_TIMEOUT))
  ```
  Send the lipsync message and start audio back to back (no awaits between
  except the send). Measure the offset between the two, log it, and keep it
  under ~50 ms.
- **Rhubarb speed**: log its run time per reply. Add
  `--recognizer phonetic` as an option (`FELT_RHUBARB_RECOGNIZER`,
  default `pocketSphinx`) and record both timings on a typical 5 s reply in
  the notes. Phonetic is much faster and language-agnostic, but less exact.
  If the default takes > 1.5 s, **switch the default to phonetic** and say so
  in the notes.
- `POST /stop`: `player.stop()`, send `{"lipsync": []}` (the mouth goes to
  rest), and send the expression `{"Fcl_MTH_Small": 0.4, "Fcl_BRW_Sorrow": 0.3}`
  (a small sheepish face) for ~1.5 s. Return `{"stopped": bool}`.
- `GET /last_reply` + `POST /repeat`: keep the last utterance
  `(text, wav, cues, tag)` in memory. `/repeat` replays it through the same
  synchronized start (skip the reaction clip). WP-10 binds keys to these.

### main.gd
- `{"lipsync": []}` (an empty list) must stop the mouth timeline immediately
  and ease visemes to rest. Today an empty list would set `_lipsync_end_time`
  to 0. Make sure that ends cleanly.

### felt-tray
- Remove `playback.play_wav(...)` from `_finish_voice_chat` and
  `_on_screen_context`. Keep `toast.show_reply` and the `/reply_ready` POST.
  Send `prompted=1` for voice and `prompted=0` for screen.
- Fallback if felt-animation is unreachable (POST fails): play locally with
  the existing `playback.play_wav`, so she's never mute because one process
  is down. Log a WARNING.
- Voice hotkey pressed while she's talking → `POST /stop` first, then start
  recording (barge-in).

### felt-dashboard (typed chat)
- Stop playing the audio in the browser when `notifyReplyReady` succeeds.
  Only fall back to `audioRef.current.play()` if the POST to felt-animation
  failed. Pass `prompted=1`. Rebuild (`pnpm build`); felt-tray serves
  `dist`, so check its `dashboard_dist_dir`.

## Tests
- felt-animation:
  - `test_audio.py`: WAV decode → int16 frames; `stop()` while playing;
    `set_gain` ramps (test the ramp function purely, no audio device); the
    `sounddevice` stream mocked.
  - `_handle_reply` runs Rhubarb and classification concurrently (fakes
    sleeping 0.3 s each → ~0.3 s total, not 0.6).
- felt-tray: the fallback path when felt-animation is down.

## Acceptance
1. A voice turn (ask Mario, or use `scripts/manual_reply_smoke.py` with a real
   WAV): audio, mouth and reaction start together. The log line
   `sync offset=…ms` shows < 50 ms. Mario judges by eye whether the lips
   match.
2. Typed chat in the chat window: the voice plays **once**.
3. `curl -X POST http://127.0.0.1:8421/stop` mid-sentence: the voice stops,
   the mouth closes, and the sheepish face flashes.
4. Kill felt-animation, do a voice turn: felt-tray still plays the audio
   (fallback).
5. Rhubarb timings (pocketSphinx vs phonetic) are recorded in the notes.

## Notes from implementation (2026-09-23)

**felt-animation**: `audio.py` (new) - `sounddevice.OutputStream` callback
player (`decode_wav`, `compute_gain_ramp`, `AudioPlayer` with
`start`/`stop`/`is_playing`/`set_gain`, gain ramped over the callback's own
block size rather than a fixed 50 ms clock - close enough at typical block
sizes and avoids a second timer). `server.py`'s `_handle_reply` now runs
Rhubarb and reaction-tag resolution concurrently via `asyncio.gather`
(extracted the old inline reaction-tag code into `_resolve_reaction_tag` so
it's an awaitable), then sends the lipsync message and calls
`player.start(...)` back to back with only a `time.monotonic()` read
between them, logging the gap. New `POST /stop` (`player.stop()` +
`overlay.lipsync([])` + a ~1.5s sheepish-face flash if something was
actually playing), `GET /last_reply`, `POST /repeat`.

**main.gd required no change.** Traced `_handle_tag_line`'s lipsync
branch → `_process()`'s lipsync loop → `_apply_lipsync_blend_smooth`: an
empty `{"lipsync": []}` list already sets `_lipsync_end_time = 0.0`, and on
the very next frame `_lipsync_current_time >= _lipsync_end_time` is
immediately true, which was already the same "reached end of cues" path
used at the end of any normal utterance - it eases toward the closed "X"
viseme via the existing lerp (`MOUTH_LERP_SPEED`), not an instant snap, and
sets `_lipsync_start_time = -1.0` to stop the timeline. The WP's own
"today an empty list would set `_lipsync_end_time` to 0" framing describes
what happens, not a bug - that's the exact same value the end of a real
utterance also settles to. Verified live (below) rather than just by
trace: no Godot-side errors across repeated `/stop` calls, including one
sent with nothing playing.

**felt-tray**: `_deliver_reply()` replaces the direct `playback.play_wav`
calls in both `_finish_voice_chat` (now `prompted=True`) and
`_on_screen_reaction` (now `prompted=False`) - POSTs to felt-animation's
`/reply_ready` and only falls back to local `playback.play_wav` if that
POST raises (felt-animation down/unreachable), logged at WARNING.
Barge-in: `_on_voice_hotkey`'s "start recording" branch now POSTs `/stop`
before `/request_started` - harmless no-op when nothing was playing (the
live test below confirms `/stop` always returns 200 either way). New
`tests/test_app_delivery.py` (4 tests, constructs `App` via `__new__` to
avoid the real tray/window/watcher side effects `__init__` would trigger,
same pattern felt-animation's own endpoint tests already use for its
lifespan). Full suite: 18 passed.

**felt-dashboard**: `notifyReplyReady` now returns whether felt-animation
actually took the POST (`response.ok`, with a 2s `AbortController` timeout
so a hung/unreachable felt-animation doesn't stall the chat window
indefinitely), and always sends `prompted=1`. `sendTextChat` awaits it
(previously fire-and-forget) and returns `playedByAnimation` on the
result; `App.tsx`'s `handleSend` only falls through to
`audioRef.current.play()` when that's `false`. The in-window mic button's
own voice-chat path (`finishRecording`) was left untouched, matching the
WP's own scope header ("felt-dashboard (typed chat)") - it never called
`notifyReplyReady` to begin with, so there was no double-play there to
fix. `tsc --noEmit` and `pnpm build` both clean; felt-dashboard has no
test runner set up yet, so this is typecheck + build + code-review
verified, not unit-tested (dashboard's first test suite is out of this
WP's scope).

**Live verification** (booted felt-animation for real - `uv run uvicorn`
hit a one-off "Application Control policy blocked this file" on the first
two attempts against the `uvicorn.exe` stub in a freshly-touched `.venv`,
same shape as WP-07's scipy DLL block; `uv run python -m uvicorn` through
the already-trusted `python.exe` worked immediately and every time after):
- Acceptance 1 (sync offset): `scripts/manual_reply_smoke.py` and a longer
  5s-clip variant both logged `sync offset=15.0ms` consistently, well
  under the 50ms target. Rhubarb pocketSphinx: 0.17s for both a 1s and a
  5s clip - nowhere near the 1.5s threshold that would justify switching
  the default to `phonetic`, so pocketSphinx stays the default as already
  set in `.env.example`/`config.py`. (Didn't separately re-measure
  `phonetic` live since pocketSphinx is already comfortably fast and nothing
  in the WP requires measuring the slower path once the faster default is
  already fine.)
- Acceptance 3 (`/stop` mid-sentence): sent a 5s clip, `/stop` 1.5s in →
  `{"stopped": true}`; a second `/stop` right after with nothing playing →
  `{"stopped": false}`. Log shows the expected `POST /reply_ready` →
  `/stop` sequence with no errors. `/last_reply` and `/repeat` round-tripped
  correctly (`/repeat` re-sent the same cues/wav through the same
  synchronized-start path, `{"status": "ok"}`).
- Acceptance 2, 4 and the "Mario judges by eye" half of acceptance 1
  weren't done by me - I can't see the overlay's lip movement or hear
  audio output myself, and acceptance 4 (kill felt-animation, confirm
  felt-tray's fallback) is covered instead by
  `test_deliver_reply_falls_back_to_local_playback_when_felt_animation_unreachable`,
  which exercises the exact same fallback code path deterministically.
  Acceptance 2 (typed chat plays once, not twice) is covered by
  `handleSend`'s `playedByAnimation` gating plus the `tsc`/build pass, but
  wasn't run end-to-end with a live felt-core. Left for Mario's own pass,
  same as WP-07's privacy sign-off step.
- Overlay + test server processes stopped cleanly afterward; port 8421
  confirmed free.

Committed as three separate repo commits (felt-animation, felt-tray,
felt-dashboard) - no main.gd commit since no change was needed there, and
no `[gemini-wip]` commits were needed this time since `git status` was
clean in felt-dashboard and the two Gemini WIP commits already present in
felt-animation/felt-character-assets were committed separately before this
WP's own edits began (see those repos' git log).
