# Phase 4 — Context awareness (WP-16, WP-17)

Read `00-implementer-context.md` first. One WP per session.

---

## WP-16

### Music: beat sync, Spotify now-playing, LRCLIB lyrics
**Repos**: felt-animation (beat detection + behaviour), felt-core (Spotify
+ lyrics, deploy), felt-character-assets (head-bob). **Size**: L. **Depends
on**: WP-15.

**Mario**: "context aware with music and stuff", and "She can have access to
the lyrics and song name directly from Spotify, I don't care if she knows the
name of the song."

**1. "Is music playing?" + beats (felt-animation, local only)**
- Capture the **default output device via WASAPI loopback**. Candidates:
  `pyaudiowpatch`, or `soundcard` (`soundcard.get_microphone(id=<default
  speaker>, include_loopback=True)`). Pick whichever works on this machine,
  and note why.
- Mono, downsampled to ~22 kHz, into **`aubio`** tempo tracking
  (`aubio.tempo("default", 1024, 512, sr)`). Nothing is recorded or sent;
  only beat timestamps and an RMS energy level exist in memory.
- **Music vs other audio**: music = a stable tempo lock (BPM within ±4 %) for
  ≥ 5 s with energy above a floor. Optionally ignore periods when the WP-09
  call monitor says someone's talking (speech is noisy for tempo).
- Behaviour:
  - A **procedural head-bob** on the beat: relay message `{"beat": {"bpm":
    …, "phase": …}}`, sent every ~2 s to re-sync. main.gd applies a small
    additive head pitch/tilt oscillation phase-locked to it, amplitude scaled
    by energy and mood.
  - A sway/foot-tap while sitting.
  - An occasional `dance` on high energy + high happiness (the WP-15 table:
    `music_start`, `music_high_energy`, `music_stop` events).
  - **Headphones prop** once props exist (WP-21 hooks the `music_*` events).

**2. Now playing (felt-core, server)**
- `spotify_client.py` already has credentials (used by `play_music`). Add
  `get_currently_playing()` → `{track, artists, album, progress_ms,
  duration_ms, is_playing}`, cached ~10 s.
- `GET /v1/music/now` returns it plus lyrics (below).
- She can answer "what's this song?" through the router (a new intent in an
  existing skill, or a `now_playing` skill with class `google_ok`).
- Unprompted track remarks: the `music_new_track` event (desktop detects it
  when the track changes via polling `/v1/music/now` every 15 s while music is
  detected), through the initiative/cooldown rules. The line is generated
  with the tone line and the track name ("oh, this one again?").
- **Taste memory** (light): a `music_taste` table tracking skips (a track
  change before 30 % of the duration) versus full plays. Surface it in the
  prompt as "Mario often skips X / replays Y", so her opinions stay
  consistent.

**3. Lyrics (felt-core)**
- Spotify's public Web API has **no lyrics endpoint**. Don't scrape the
  private one (token hacks, ToS). Use **LRCLIB**:
  `GET https://lrclib.net/api/get?track_name=…&artist_name=…&album_name=…&duration=<s>`
  (no key; send a descriptive `User-Agent`). Prefer `syncedLyrics` (LRC)
  over `plainLyrics`. Cache per track id on disk (`data/lyrics/`), and cache
  misses too.
- Uses:
  - a line she can quote in a remark;
  - **mouthing along**: during a chorus (the most-repeated LRC line), now and
    then send a viseme timeline built from the synced lyric timings (a vowel
    shape per word, reduced amplitude, **no audio**) with eyes half-closed;
  - lyric mood can nudge the face.
- Lyrics text may go to Gemma for the remark (public content).

**Tests**: tempo-lock decision as a pure function over synthetic beat
streams; the LRC parser; LRCLIB client with a mocked HTTP layer; skip/full-play
classification.

**Accept**: play a song; within ~10 s she bobs on the beat. Ask "what's this
song?" and she answers correctly. Occasionally she remarks on a new track or
mouths along to a chorus. With music off she stops bobbing.

### Notes from implementation (2026-09-23)

**Part 1 (beat detection + head-bob) built, committed, partially verified live:**

- `aubio` has no prebuilt wheel for Windows/Python 3.12 and its source build
  needs an MSVC toolchain not installed on this machine. Rather than install
  full Visual C++ Build Tools for one nice-to-have feature, wrote a from-
  scratch numpy-only onset/tempo tracker instead (`felt_animation/beat.py`):
  RMS-windowed onset detection, inter-onset-interval clustering, a
  `TempoLock` state machine matching the spec's "BPM within ±4% for ≥5s"
  literally. 22 unit tests recover known BPM (120/128/140) from synthetic
  click tracks, clean and jittered.
- `sounddevice` (already a dependency) has no WASAPI loopback support in the
  build available here (`WasapiSettings(loopback=True)` raises `TypeError`
  on this machine). Switched to `pyaudiowpatch` for capture
  (`felt_animation/beat_capture.py`). Verified against real audio (non-zero
  peak amplitude).
- Head-bob wired as a third additive layer on Head in main.gd (alongside the
  WP-13 nod-pulse and WP-14 gaze), reusing the established
  `_apply_additive_once` composition helper and the explicit-stop pattern
  (`beat.active=false` zeroes the layer rather than being inferred from
  messages no longer arriving). Godot headless syntax check clean.
- Mood-gated `dance` ambient weight and `/status` exposing
  `music_locked`/`music_bpm` also done.
- **Live tempo-lock convergence does not work yet.** Tested against both a
  synthetic click track (two variants, 120 BPM) and ~2 minutes of real
  Spotify audio via the live loopback capture. On the synthetic click track,
  estimates found harmonically-plausible values but kept jumping between
  plateaus rather than holding one long enough to cross the 5s lock
  threshold. On real music the estimates were considerably worse — no
  plateau at all, bouncing across roughly 54-184 BPM (octave/fraction-
  related values of each other) tick to tick over the full window, never
  once approaching a lock. This is a real gap between the unit-test
  environment (clean synthetic onset timestamp arrays) and live audio
  (polyphonic real music has several competing periodicities - kick, snare,
  vocal transients - that a single-band RMS onset detector can't
  distinguish, unlike `aubio`'s spectral-flux based tracker). Not chasing
  this further live for now (see `mario-defer-live-debugging` memory) -
  likely needs either a spectral-flux onset function instead of RMS, or
  band-limiting to a bass/kick range before onset picking. Left as a known
  limitation; the bob mechanism itself (main.gd side) has not yet been
  visually confirmed either, since it depends on a lock ever engaging.
- Part 2 (Spotify now-playing) and Part 3 (LRCLIB lyrics) not started.

---

## WP-17

### Signals: game start/stop, AFK, GPU heat, rage-click rate, call energy
**Repos**: felt-animation (a new `signals/` package), felt-core (lines, via the
existing endpoints). **Size**: M. **Depends on**: WP-15.

All local, all deterministic. Each signal emits a WP-15 reaction-table
**event**. Most reactions are non-verbal; speech goes through the cooldown and
initiative rules.

| Signal | How | Events |
|---|---|---|
| Game/app launched or closed | a `psutil` process poll every 5 s, against a configurable `games.toml` (exe names; seed it by asking Mario, and record the first detections in the log) | `game_start(name)`, `game_stop(name, duration)` → comfy pose / "finally done?" |
| AFK | `GetLastInputInfo` | `afk_start` (> 10 min: bored → book/nap via WP-21 props later), `afk_end(duration)` → greeting when he's back (a spoken line if it was a long absence) |
| Rage clicking / key mashing | a low-level mouse+keyboard hook that **counts events only, never records keys** (`pynput` listeners, count per second; discard everything else) | `mash` (above ~8 clicks/s sustained for 3 s) → flinch / "easy there" face |
| PC under load | GPU temp and usage. AMD RX 6700: use **LibreHardwareMonitor** (its WMI provider or the `LibreHardwareMonitorLib` via pythonnet). Verify what's installable and working on this machine | `gpu_hot` (> ~80 °C sustained) → fans herself |
| Call energy | the WP-09 call-monitor peak, smoothed | `call_lively` (sustained high energy/laughter-ish bursts: amplitude only, **never content**) → smiles / giggles; `call_quiet` |
| Friend joins the call | a new Discord audio burst after > 2 min of silence (a heuristic; note its limits) | `call_join_guess` → a small wave toward the screen |

**Notifications**: *skip for now.* `UserNotificationListener` may need package
identity for an unpackaged Python app. Only pursue it if a quick test shows
it works; otherwise record the finding.

**Tests**: each detector as a pure function over synthetic samples
(thresholds, hang times, debounces).

**Accept**: launching and closing a listed game, going AFK for 10+ min, mashing
clicks, and a lively call each produce a visible reaction. The logs show the
events. No keystroke content anywhere (review the hook code with Mario).
