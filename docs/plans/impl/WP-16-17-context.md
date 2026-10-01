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
**Part 2 (Spotify now-playing + taste memory) - built, deployed, live-verified:**

- `spotify_client.get_currently_playing` (10s-cached), a `now_playing` skill
  ("what's this song?", `google_ok`), and `GET /v1/music/now` for felt-tray's
  poll. `music_taste_loop` classifies each finished listen as a skip (<30% of
  duration) or full play and persists it; `music_taste.summarize_taste` folds
  that history into a "Mario often skips X / plays Y through" prompt note on
  both the local and cloud chat paths (music is cloud-ok per Mario's own
  google_ok stance, unlike facts).
- **Live-verified against the real deployed server**: `/v1/music/now`
  correctly tracked a real track change between two checks; "what song is
  this?" routed through the real router to `now_playing`, hit the real
  Spotify API, and came back as real phrased/spoken audio; clean container
  logs throughout.

**Part 3 (LRCLIB lyrics) - built, deployed, partially live-verified:**

- `lyrics_client.py`: LRC parser, chorus detection (most-repeated line, 3+
  occurrences), current-line-by-position lookup, and `get_lyrics` against
  LRCLIB (public, keyless - Spotify's own API has no lyrics endpoint),
  permanently disk-cached per track id including negative results.
  `GET /v1/music/lyrics` exposes it; `now_playing` best-effort quotes the
  current lyric line when one exists.
- **Mouthing along**: felt-animation's `lipsync.synthetic_mouth_along_cues`
  builds a plausible, non-audio-derived mouth timeline (subdued-weight
  visemes only) in the same shape Rhubarb's real cues use, so main.gd plays
  it with zero new code there - it already eases back to closed once the
  duration's up. `POST /mouth_along` plays it, gated only by hush. **Scope
  cut**: "eyes half-closed" not implemented - no verified eye-closure
  blend-shape primitive exists yet (WP-14's gaze controls where she looks,
  not eyelids).
- **The trigger**: closes Part 2's own open loop (felt-core has no
  continuous playback-position awareness) - felt-tray's new
  `_music_poll_loop` (15s, same cadence the plan specifies) both fires the
  unprompted new-track remark (via `send_screen_context`, so it's still
  felt-core's own initiative/cooldown decision, not a guaranteed remark) and
  rolls a flat per-poll chance to mouth along when inside a detected chorus
  window, capped once per track.
- **Live-verified**: `/v1/music/lyrics` responds correctly deployed; the
  new-track-remark path is live (felt-tray's poll hits `/v1/music/now` every
  15s in the real running process). **Not live-verified**: the actual
  chorus/mouth-along firing end-to-end (LRCLIB returning real synced lyrics
  for a real currently-playing track, landing inside its chorus window,
  winning the probability roll) - Spotify wasn't playing at the point this
  was checked. The `/mouth_along` endpoint itself WAS live-verified directly
  (moved the real connected overlay's mouth; correctly no-ops while hushed).

**Verified**: 286 felt-core tests (up from 237 pre-WP-16), 219 felt-animation
tests, 105 felt-tray tests, all passing. Deployed to the real server twice
(Part 2, then Part 3) via the documented archive/vendor/push/systemctl flow,
both clean deploys with a passing health check.

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

### Notes from implementation (2026-09-24)

**Built, live-verified, mostly working:**

- New `felt_animation/signals/` package: `games.py`, `afk.py`, `mash.py`,
  `gpu.py`, `call_energy.py` - one clock-injectable pure tracker class per
  signal (same style as `presence.PresenceState`/`call_monitor.TalkingDetector`)
  plus the real OS-touching sampling function each wraps. 30 new pure-logic
  tests, all against synthetic samples per the WP's own Tests section.
- `server.py`'s `signals_loop` (5s: games/AFK/GPU) + `mash_loop`/
  `call_energy_loop` (1s each) feed a shared `_fire_signal_reaction` helper -
  a mood-weighted face pose (`reactions.json`'s new `game_start`/`game_stop`/
  `mash`/`gpu_hot`/`call_lively`/`afk_end`/`call_join_guess` entries, same
  mechanism as `idle_micro`/`reply:<emotion>`) plus a body clip for the few
  events with a real matching one in the library
  (`afk_end`→`greeting`, `call_lively`→`emotion/laughing`,
  `call_join_guess`→`gesture/wave`).
- `games.toml` seeded with only `endfield.exe` (confirmed real, seen live
  during a WP-16 test) - the rest of what Mario actually plays needs to come
  from him, per the WP's own "seed it by asking Mario," not a guessed list.
- **Live-verified with a real process**: temporarily added `notepad.exe` to
  the watchlist, launched and closed it for real - `game_start(notepad.exe)`
  and `game_stop(notepad.exe, 15s)` both fired correctly with a real
  duration, `/status` tracked `games_running` accurately throughout. Reverted
  back to the committed watchlist afterward.
- **Live-verified for real**: `call_lively` fired end-to-end during an actual
  live call (real peak samples → smoothing → sustained-threshold → face pose
  + `emotion/laughing` clip), no synthetic data involved.
- `idle_seconds()` (AFK) and `running_game_exes()` (games) both confirmed
  working against real OS state (`ctypes.GetLastInputInfo`, real `psutil`
  process enumeration).

**Deliberate scope cuts, flagged rather than silently done:**

- **Speech**: every signal is non-verbal only, even where the WP's table
  suggests a line (`game_stop`'s "finally done?", `afk_end`'s "a spoken line
  if it was a long absence"). felt-animation has no local TTS - every real
  spoken reply on this whole project flows the other direction (felt-core
  generates text+audio, then POSTs it here); making felt-animation originate
  speech for these two would mean either reversing that call direction for
  the first time anywhere in the project, or a set of pre-recorded canned
  lines. Neither felt like a decision to make silently inside an otherwise
  self-contained WP - the non-verbal half (pose + the greeting/laughing/wave
  clips) still fires for both.
- **`afk_start`**: fires and logs, but produces no reaction at all - the
  WP's own text defers its reaction ("bored → book/nap") to WP-21's props
  system, which doesn't exist yet, same as WP-15's own "no AFK detector
  exists yet" note (which now has a real signal to feed, if wanted later).
- **`gpu_hot`**: GPU heat detection is fully built (LibreHardwareMonitor
  installed via choco through the scoped elevation dispatcher, `read_gpu_temp_c`
  queries its WMI provider, `GpuHeatTracker`'s threshold logic tested) but
  **not live-verified** - LibreHardwareMonitor only exposes its WMI provider
  while running WITH ADMINISTRATOR RIGHTS, and there's no way to get it
  running elevated without a real interactive UAC click (the elevation
  dispatcher's allowlisted `Register-ScheduledTask` uses `LogonType S4U` with
  no `RunLevel Highest`, so a task registered through it would still run
  unprivileged). **This needs Mario**: launch
  `C:\ProgramData\chocolatey\lib\librehardwaremonitor\tools\LibreHardwareMonitor.exe`
  once, approve the UAC prompt, and in its Options menu enable "Run on
  Windows Startup" + "Minimize to tray" so it's there every session. Once
  that's done `/status`'s `gpu_temp_c` field should start reporting a real
  number instead of `null`.
- **The keyboard/mouse hook** (`mash.py`'s `EventCounter`): built with counts-
  only as a hard invariant (never stores which key/button, see the module's
  own docstring), and the pynput listener itself was live-verified to start/
  stop cleanly. Per the WP's own Accept criterion, this file specifically
  still needs an explicit read-through with Mario before being considered
  fully signed off - not something an automated test can substitute for.

**Verified**: 292 felt-animation tests passing (255 before this WP + 37 new:
30 signal-detector tests + a handful folded into the count above). Not yet
pushed through a full end-to-end AFK (would need a real 10-minute idle wait)
or mash (would need real sustained clicking) live test - both are covered by
unit tests against the exact same decision logic real samples flow through,
same confidence level WP-16's tempo-lock tests had before its live gap
showed up, so flagged as "logic verified, live end-to-end not yet watched"
rather than claimed as fully proven.

### Follow-up (2026-09-26): automatic game detection

Mario's review call: "use the window title and recognize every game, no
need to specify". `signals/games.py` now treats a windowed process as a
game when its exe is under a library root (Steam `libraryfolders.vdf` ->
`steamapps\common`, Epic manifests' `InstallLocation`, GOG registry
`path`, games.toml `roots`), is in Windows' GameConfigStore
(`MatchedExeFullPath`; `ExeParentDirectory` is only a folder name here, so
unused), or is named in games.toml `games`. A built-in ignore list
(launchers, helpers, crash handlers, anti-cheat, VR runtime, Wallpaper
Engine, embedded web views, `*launcher*`/`*crash*`/... patterns) plus
browsers/Discord/Felt itself, plus games.toml `ignore`. `details.name` is
the cleaned window title; tracking is keyed by exe path, with hysteresis
(a tracked game stays running while its process lives, window or not).
On this machine: Steam libraries `C:\Program Files (x86)\Steam` and
`F:\SteamLibrary`, no Epic/GOG, 5 GameConfigStore exes, and `F:\Games`
added as a games.toml root (Endfield/GRYPHLINK, FFXIV, WoW, Factorio).
`games.exe` (the GRYPHLINK launcher window) is in games.toml `ignore`.
Commit `31405ce` in felt-animation, 388 tests passing.

**2026-10-01 review, done on evidence:** across 9 days of logs, every
WP-17 signal fires (game_start/stop 33/10, afk 24, mash 3, call
lively/quiet 348/326) except `gpu_hot`. That was dead because the reader
needed LibreHardwareMonitor running elevated, which was never set up on
the Windows install. Mario picked option A: `signals/gpu.py` now reads
AMD's ADL (`atiadlxx.dll`, PMLog sensor 8 = edge) in user mode, with LHM
as the fallback (felt-animation `7d06191`). The RX 6700 sits at ~82 °C in
games, so hot is ≥ 85 °C sustained for 10 s, at most once per 30 min. The
reaction row's `gesture/fan` clip never existed (Mario: "I don't think we
have a fan herself emote"), so she drinks from her water bottle instead
(`reaction:water_bottle`, the drink_water clip). felt-core's line was
changed to match (`d1dd4c0`).
