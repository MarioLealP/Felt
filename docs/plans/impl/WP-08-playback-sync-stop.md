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
