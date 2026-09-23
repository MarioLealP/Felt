# Phase 3 — Face and body (WP-11 … WP-15)

Read `00-implementer-context.md` first. Each WP below is its own session.

---

## WP-11

### MSAA anti-aliasing
**Repo**: felt-character-assets. **Size**: S. **Depends on**: none.

**Why**: Mario: "she needs antialiasing." `project.godot` has
`renderer/rendering_method="gl_compatibility"` (OpenGL, chosen because the
Vulkan path crashed the AMD driver with the transparent overlay) and
`anti_aliasing/quality/msaa_3d=0`, so no AA at all. FXAA/TAA aren't offered
by the Compatibility renderer and would smear transparent edges anyway.

**Do**:
- Set `anti_aliasing/quality/msaa_3d=2` (4×) in `project.godot`.
- Rebuild, run, and check **against a light and a dark wallpaper**: smooth
  silhouette and hair edges, and **no dark halo/fringe** around her outline.
  The transparent window's edge alpha must blend as premultiplied.
- If there *is* a dark fringe, check how Godot writes alpha for the transparent
  framebuffer in Compatibility mode, and try
  `rendering/viewport/transparent_background` handling or a final
  premultiply pass. Document what worked.
- Measure GPU usage before and after (Task Manager is fine) and note it.
- Supersampling for texture shimmer comes later with the small follow-window
  (WP-22). Don't do it here.

**Accept**: Mario confirms edges look smooth, with no halo.

### Notes from implementation (2026-09-23)

`msaa_3d` set from 0 to 2 (4x) in `project.godot` - one line. Verified via
the directly-run Godot workaround already in use this session for WP-09/10
(no export needed - MSAA is a runtime rendering setting the engine reads
regardless of how the project was launched, not something baked into the
export step): GPU 3D engine utilization measured (via
`Get-Counter '\GPU Engine(*engtype_3D)\Utilization Percentage'`, 3 samples
each) went from ~56% at msaa_3d=0 to ~63% at msaa_3d=2 for the same idle
scene - a real but modest cost. A screenshot crop around her hair/shoulder
silhouette shows clean, smooth edges with no obvious dark halo/fringe
against the light desktop background actually behind the transparent
window at check time.

**Not checked - the WP explicitly asks for it**: a DARK wallpaper
specifically (only the current, light one was available without changing
Mario's actual desktop background, which felt like an intrusive thing to
do unasked). Left unticked pending that check and his own final call on
whether the edges genuinely look right to him.

---

## WP-12

### Face compositor + procedural face life
**Repos**: felt-character-assets (main.gd), felt-animation. **Size**: L.
**Depends on**: WP-08.

**Why**: Mario: "just having her move her face other than blink and yap would
go a long way." The model (`felt.vrm`) has **57 VRoid face shapes, split by
region**:
- **Brows**: `Fcl_BRW_{Angry,Fun,Joy,Sorrow,Surprised}`
- **Eyes**: `Fcl_EYE_{Natural,Angry,Close,Close_L,Close_R,Fun,Joy,Joy_L,Joy_R,Sorrow,Spread,Surprised,Iris_Hide,Highlight_Hide}`
- **Mouth**: `Fcl_MTH_{A,I,U,E,O,Neutral,Close,Up,Down,Angry,Small,Large,Fun,Joy,Sorrow,Surprised,SkinFung,SkinFung_L,SkinFung_R}`
- **Teeth**: `Fcl_HA_*`
- plus `Fcl_ALL_*` whole-face presets.

Today only the `ALL` presets (via a keyword map), blink and visemes are used.
`ALL` shapes include a mouth, so they fight lipsync. The VRM `lookAt` type is
**bone** (real eye bones).

**main.gd: region compositor**
- Four channels, **brows / eyes / mouth / teeth**, each with a target dict
  `{shape: weight}` and its own easing (the eyes are faster). Stop driving
  `Fcl_ALL_*`.
- **While lipsync is active, the mouth channel belongs to visemes.** Emotion
  reaches the mouth only through `Fcl_MTH_Up`/`Fcl_MTH_Down` at ≤ 0.5 weight
  (smile/frown corners layer over visemes).
- Blink stays procedural, but must *multiply against* eye-close shapes already
  set (a sleepy half-lid plus a blink shouldn't exceed 1.0).
- New relay message: `{"face": {"pose": "<name>", "intensity": 0..1, "hold":
  seconds}}` or `{"face": {"regions": {"brows": {...}, "eyes": {...},
  "mouth": {...}}, "hold": s}}`. After `hold`, ease back to the **resting
  face** (below). Keep the old `{"expression": …}` message working by mapping
  it onto the regions.

**felt-animation: pose vocabulary + face life**
- `face_poses.json` (data, tunable). Starting set (weights approximate; tune by
  eye):

  | Pose | Shapes |
  |---|---|
  | `soft_smile` | EYE_Joy .3, MTH_Up .5 |
  | `grin` | EYE_Joy .8, BRW_Joy .6, MTH_Fun .7 |
  | `smug` | BRW_Fun .5, EYE_Joy_L .5, MTH_Up .5, MTH_SkinFung .4 |
  | `wink` | EYE_Close_R 1, MTH_Up .6 |
  | `pout` | BRW_Angry .4, MTH_Small .8 |
  | `thinking` | BRW_Sorrow .25, MTH_Small .3 (+ gaze up-left in WP-14) |
  | `sleepy` | EYE_Close .45, BRW_Sorrow .2 |
  | `wide_eyed` | EYE_Spread .8, BRW_Surprised .8 |
  | `shocked_comedic` | EYE_Surprised 1, EYE_Highlight_Hide 1, MTH_Large .6 |
  | `annoyed` | BRW_Angry .6, EYE_Angry .4, MTH_Down .4 |
  | `sad` | BRW_Sorrow .7, EYE_Sorrow .5, MTH_Down .5 |
  | `embarrassed` | BRW_Sorrow .4, EYE_Joy .4, MTH_Small .5 |
  | `curious` | BRW_Surprised .4 |
  | `sheepish` | BRW_Sorrow .3, MTH_Small .4 (used by WP-08 `/stop`) |

  There's no single-brow shape, so no one-eyebrow skepticism.
- **Emotion → pose map**: map the WP-07 `emotion` values (`happy, excited,
  amused, sad, annoyed, surprised, thinking, sleepy, neutral`) to poses.
  felt-core replies carry `X-Emotion` (added by WP-07 for screen; add the same
  JSON field to the skill/chat cloud calls here, or map from the reaction tag
  as a fallback).
- **Face-life loop** (runs whenever she's visible and not in a hold):
  - **Micro-expressions** every 5–20 s: a flicker of `soft_smile`, a brow raise
    (`curious` at 0.3 for 0.6 s), a tiny `pout`, a glance-and-smile. Weighted,
    with no immediate repeats.
  - **Resting face**: `neutral` for now. WP-15 will drive it from mood
    (content → a faint `soft_smile` at 0.15, bored → a heavier lid, etc.).
- **Speech accents**: while audio plays, detect envelope peaks in the WAV
  (RMS over 50 ms windows; peaks above the rolling mean by 1.5×). On each
  peak, send a short brow raise (BRW_Surprised 0.25 for 0.25 s). At the end
  of a line whose emotion is happy/amused, finish with a `soft_smile`.
- Replace `_EXPRESSION_KEYWORDS` usage in `_handle_reply` with
  emotion/tag → pose.

**Accept**: side by side with the old build, Mario sees her face moving even
while idle, expressions visibly change during speech without breaking the
lips, and nothing looks twitchy. Tune the frequencies with him.

### Notes from implementation (2026-09-23)

Built essentially the whole WP: `face_poses.json` (all 14 named poses from
the table above), `faces.py` (region classification from shape-name
prefix, pose->regions splitting, emotion/tag->pose mapping),
`face_life.py` (micro-expression picking with no immediate repeats, RMS-
envelope peak detection over the reply WAV for speech accents), and
main.gd's region compositor (brows/eyes/mouth/teeth, independent easing
speeds, the mouth-channel Up/Down-only-≤0.5 filter, blink multiplied
against whatever eye-close shape the compositor already has active).
133 felt-animation tests passing (31 new).

**Two real design bugs found and fixed during implementation, before
either ever shipped** (caught by re-reading my own design against the
actual message flow, not live-discovered this time):
1. `_set_face_regions` originally reset ALL FOUR regions on every
   incoming message, including ones the message didn't mention. A brief
   brow-raise accent (`{"regions": {"brows": {...}}}`) would have wiped
   the reply's own eyes/mouth pose back to empty the instant it arrived.
   Fixed to only touch regions actually present in the message.
2. The hold timer was originally one global deadline. The same brow-raise
   accent's own short hold (0.25s) would have reset that global timer,
   so 0.25s later ALL regions - including the reply's own multi-second
   pose hold on eyes/mouth - would have eased back to resting mid-reply.
   Fixed to per-region hold timers (`_face_region_hold_until_ms`, a
   dict keyed by region, not a single float).

**Scoped narrower than the WP's own text in one place, deliberately**:
felt-core doesn't send an `emotion` field on chat/skill replies (only
WP-07's screen reactions have real emotion classification, and even that
doesn't currently reach felt-animation - felt-tray's `_deliver_reply`
never forwards `result.emotion` to `/reply_ready`). Rather than extend
felt-core (a third repo, not in this WP's own header) or felt-tray (ditto)
just for this, used the WP's own explicitly-offered fallback: map from the
resolved animation tag's keywords instead, same spirit as the old
`expressions.py` this replaces. A real emotion passthrough - especially
for screen reactions, where felt-core already computes one and it's
currently just discarded - is a genuine, fairly small follow-up, not
something this WP required.

**Not done - needs a live Godot instance, which isn't running right now**
(a background-pressure safety reap killed the one from earlier in this
session, along with the felt-animation server testing it; per its own
instructions, not relaunching either on my own right now): the region
compositor was only verified via a headless parse/load check (no runtime
errors, including catching a real static-typing bug before it shipped -
see main.gd's own commit) - never actually seen rendering, never seen
receiving a real `{"face": ...}` message from a live felt-animation
`_handle_reply` call. The WP's entire Accept criterion ("Mario sees her
face moving... nothing looks twitchy... tune the frequencies with him")
is his own live, side-by-side judgment call regardless - this just isn't
even at the point of being watchable yet. Next step once a Godot instance
is back up: send a few real `{"face": {"regions": ...}}` messages by hand
and confirm nothing crashes or looks obviously wrong before asking Mario
to actually judge it.

---

## WP-13

### Listening pose + backchannel nods
**Repos**: felt-tray, felt-animation. **Size**: S. **Depends on**: WP-08.

**Why**: felt-tray fires `/request_started` when voice recording *starts*
(`app.py::_on_voice_hotkey`), so she plays "thinking" while Mario is still
talking. A `reaction/listening` clip exists and is never used.

**Do**:
- felt-animation `POST /listening_started` → play `reaction/listening`
  (resolve it with `resolve_known_tag`) looping via the same mechanism as the
  thinking loop, plus a slight head tilt / `curious` 0.3 face.
  `POST /listening_stopped` ends it.
- felt-tray: hotkey press → `/listening_started`; hotkey release (recording
  stops) → `/listening_stopped` then `/request_started` (thinking), as now.
- **Backchannel**: felt-tray already has the mic stream. Compute RMS per
  ~50 ms. When Mario has spoken for > 1.5 s and then pauses 400–700 ms, POST
  `/nod`. felt-animation plays a small nod: `gesture/nodding` at low
  intensity if available, else a procedural head-pitch pulse (add a
  `{"nod": 1}` relay message; main.gd applies an additive ~6° head pitch dip
  over 0.35 s). Rate limit it to 1 per 2 s.

**Accept**: during a voice message she looks like she's listening and nods at
pauses; thinking starts only after release.

### Notes from implementation (2026-09-23)

Built the whole WP: `/listening_started`/`/listening_stopped` (reusing
`state.py`'s existing begin_thinking/end_thinking_and_wait machinery -
listening is just another tag to loop, same mechanism thinking already
uses, not a new one), felt-tray's `BackchannelDetector` (speech-then-pause
timing, pure/clock-injected, wired into `Recorder`'s own mic callback so
no separate capture pass is needed), and main.gd's nod pulse (additive
Head-bone pitch dip, applied after the AnimationPlayer via the same
process_frame hook `_clamp_feet_to_floor` already uses).

**Deliberately used the procedural pulse, not `gesture/nodding`, for
every nod** - the WP offers both as options ("gesture/nodding at low
intensity if available, else a procedural pulse"), but `gesture/nodding`
is a full body-animation clip, which would need the SAME activity lock
the listening loop is already holding for its entire duration
(`state.begin_thinking`'s own `async with self._activity_lock`) - a nod
fired mid-listening would just queue up behind the lock and play late
(or never, if listening ends first), not actually nod while Mario's
genuinely mid-pause. The procedural pulse sidesteps this entirely since
it's an additive rotation, not something that needs the lock at all.

**`FELT_BACKCHANNEL_RMS_THRESHOLD` (default 500) is an unverified
starting guess** - same situation as WP-09's call-ducking threshold,
needs a real session with Mario talking to tune against his actual mic
gain.

**Live-verified**: `/listening_started` → a screenshot showed a real,
visibly distinct animated pose (not idle) - confirms the listening loop
actually plays a real clip, not a silent no-op. `/nod` and
`/listening_stopped` both completed with no errors anywhere in the log
across several calls. **Not verified**: the actual voice-hotkey press/
release flow end to end (felt-tray's own hotkey handlers were only unit-
tested, not exercised through a real keypress), whether the nod pulse
actually LOOKS like a nod rather than a glitch, and whether the
backchannel threshold ever correctly fires on Mario's real voice - all
three need a live session with him.

---

## WP-14

### Gaze: head and eyes follow the cursor, look at camera
**Repo**: felt-character-assets (main.gd) + a little felt-animation.
**Size**: M. **Depends on**: WP-12.

**Do (main.gd, procedural, runs after the AnimationPlayer each frame, same
hook as `_clamp_feet_to_floor`)**:
- **Target**: the mouse cursor position (`DisplayServer.mouse_get_position()`
  works while the window is click-through) converted to a world point on a
  plane in front of her. Or `camera` (look at the viewer), or `none`.
- **Head/neck**: additive rotation on the `neck` + `head` bones (split ~40/60),
  clamped to ±35° yaw and ±20° pitch, smoothed (critically damped, ~0.25 s).
  Apply it **on top of** the animated pose, so clips still play.
- **Eyes**: rotate the eye bones (VRM lookAt type is bone; find `leftEye` /
  `rightEye` humanoid bones), clamped to ±12°. Add **saccades**: every 0.5–3 s
  a small random offset (±2–4°) that snaps within ~40 ms; blink on large
  (> 10°) gaze jumps.
- **Behaviour** (driven by felt-animation via `{"gaze": {"mode":
  "cursor"|"camera"|"point"|"none", "x":…, "y":…}}`):
  - default `cursor` while the cursor moves;
  - after 4 s of cursor stillness → `camera` (she looks at Mario);
  - while speaking → `camera`;
  - on a screen reaction → `point` at the reacted window's rect centre for
    ~1.5 s, then `camera` (felt-tray/WP-07 knows the rect; pass it through
    `reply_ready`);
  - `thinking` → up-left point.
- Blend weight 0 during clips where head control would look wrong (e.g. while
  lying/falling in later WPs): a per-tag opt-out list in felt-animation.

**Accept**: she follows the cursor naturally, glances at Mario when he stops
moving, and never snaps or breaks clips.

### Notes from implementation (2026-09-23)

Built the whole WP: main.gd's additive head/neck/eye rotation (same after-
AnimationPlayer technique WP-13's nod pulse established), saccades, blink-
on-large-jump, and the `{"gaze": {"mode", "x", "y"}}` relay message; plus
felt-animation's small piece - `overlay.gaze()` and the "thinking sends an
up-left point" wiring in `request_started`/`_handle_reply`.

**Bone names confirmed live before writing anything against them** - dumped
the real skeleton's full bone list from a running instance rather than
guessing from the WP text's `neck`/`head`/`leftEye`/`rightEye` naming
(VRM-spec names). The real names on this skeleton turned out to be
PascalCase with no prefix (`Neck`, `Head`, `LeftEye`, `RightEye`), matching
`_clamp_feet_to_floor`'s already-working `LeftFoot`/`RightFoot` convention,
not the spec names - would have silently no-op'd every gaze rotation if
guessed wrong, the same class of bug the WP-09 bubble scare turned out not
to be but easily could have been.

**Deliberately narrower than the WP's own text in one place**: "on a
screen reaction → point at the reacted window's rect centre" needs
felt-tray to pass real window-rect coordinates through `reply_ready`, and
felt-tray isn't in this WP's own repo header (`felt-character-assets` + "a
little felt-animation"). Built the `point` mode itself (verified live,
works correctly for the in-scope "thinking" case), but not the specific
caller that would feed it a screen-reaction rect - a real, fairly small
follow-up if Mario wants it, not required by this WP as scoped.

**"While speaking" needed no explicit message at all** - main.gd already
tracks whether she's actively lipsyncing (`_lipsync_start_time >= 0.0`)
from WP-08, so gaze reads that directly each frame and overrides to camera
locally, with zero extra network traffic and zero risk of felt-animation
forgetting to send a follow-up. Only the two cases main.gd genuinely can't
infer on its own (thinking, and the out-of-scope screen-reaction point) go
through the explicit message.

**Live-verified**: a headless load caught one real static-typing bug
(fixed before it shipped - an untyped `:=` on a bone-lookup return value,
same class of issue WP-12 also hit once). A real running process cycled
through all four modes (`cursor`/`camera`/`point`/`none`) with zero
crashes. Sent `point` mode at opposite viewport edges (x=0.05 vs x=0.95)
and compared screenshots - the two head turns are clear mirror images of
each other, confirming the yaw computation actually responds to input and
is directionally *consistent* (a genuine, checkable fact from a static
image). **Not verified from a screenshot, and can't be**: whether "left"
in the code actually matches "left" on Mario's real screen from his own
cursor, and whether the motion looks natural in real time rather than
mechanical - both are exactly the WP's own Accept criterion, and need him
watching it live, moving his own mouse.

### Update (2026-09-23, live with Mario): head/neck ships, eyes disabled

Head/neck gaze tracking held up under real live use - after fixing the
runaway-rotation and inverted-pitch bugs below, no further complaints
about it. **Eye rotation did not.** Three live bugs in sequence, each
looking fixed at the time:

1. **Runaway spin, cursor-tracking invisible under it.** Root cause:
   `get_bone_pose_rotation()` was read every frame as if it were always a
   fresh AnimationPlayer-driven baseline and multiplied by a new additive
   (`current * additive`). It isn't, at least for the idle clips - once a
   track stops changing (or the bone has no track at all), nothing
   rewrites it, so "current" on frame N was actually our own output from
   frame N-1. A bounded per-frame offset became unbounded compounding.
   Fixed with a shared `_apply_additive_once` helper that tracks exactly
   what each layer (gaze, and the WP-13 nod pulse - identical bug, just
   less visible as a brief self-decaying pulse) applied last frame and
   divides it back out before reapplying.
2. **Vertical inverted.** The Head bone's local RIGHT axis pitches the
   opposite way from the naive "up is positive" assumption on this
   skeleton. Negated at the source.
3. **Eyes pointing forward regardless of head rotation.** LeftEye/
   RightEye are children of Head - applying their own world-target
   rotation as an independent additive double-counted whatever neck+head
   had already turned. Fixed by dividing out the neck+head contribution
   first.

Then, checking again live: **one eye under the bottom eyelid, the other
normal, inverting on blink** (the inversion was very likely just a side
effect of the same bug - a wrong/extreme eye angle is itself a large
gaze jump, which the existing blink-on-jump logic fires on). Dumped the
real bone rest bases live rather than guessing again: Head/Neck rest is
identity, but LeftEye/RightEye rest is a genuine 90-degree rotation,
*identical* for both eyes - ruling out a mirrored-rig convention, my
first guess. The actual bug: `_apply_additive_once` composed
`baseline * additive` (post-multiply), which is harmless when rest is
identity (Head/Neck) but wrong when it isn't (eyes) - it treats the
fixed axis labels as relative to the bone's own rotated rest frame
instead of the reference frame Mario's cursor actually moves in. Fixed
to `additive * baseline` (pre-multiply).

Checked again live: **pupils gone entirely.** Two eye-specific fixes in
a row, each reasoned through carefully, each wrong or incomplete in a
new way once actually seen. Per Mario's own standing preference (stop a
live debugging exchange that isn't converging rather than keep offering
one more fix), **eye rotation is disabled** - `_apply_eye_gaze` is no
longer called; `LeftEye`/`RightEye` are explicitly reset to their rest
rotation every frame instead (not just left alone, since whatever the
last live test left them at was mid-broken). Head/neck tracking alone is
confirmed working and is what's shipped. Re-enabling eyes needs real
empirical A/B testing of the composition order - screenshot both options
side by side before trusting either - not another round of reasoning it
out and trying live.

**FLAGGED (2026-09-23): doesn't work.** Mario checked head/neck tracking
live himself (the WP's own Accept criterion, which a screenshot can't
verify) and it doesn't hold up - "doesnt work." No further detail given
yet on what specifically is wrong (direction, smoothness, responsiveness,
something else). Not investigated further per his "flag it and go on" -
circling back later rather than debugging blind without knowing which
part failed. WP-14 stays unchecked in the status table.

---

## WP-15

### Mood × time-of-day + reaction table + tone line
**Repos**: felt-animation, felt-core (deploy). **Size**: L. **Depends on**:
WP-07, WP-12.

**Why**: Mario chose "time of the day / mood approach, that would make her the
most natural" for her commentator personality, and reactions must be
data-driven.

**Do**:
- felt-animation `mood.py`: a persistent vector `{energy, happiness, boredom,
  affection, annoyance}` in 0..1, saved to `%APPDATA%\Felt\mood.json`.
  - **Drift**:
    - energy follows a daily curve (low 1–7 am, peak afternoon);
    - boredom rises with no events or reactions for a while;
    - annoyance decays over ~30 min.
  - **Events nudge it**:
    - reaction spoken +happiness small;
    - hush used +annoyance;
    - windows closed under her (later) +annoyance;
    - Mario talking to her +affection/+happiness;
    - long AFK +boredom.
  - A partial reset each morning.
- `tone.py`: builds a one-line **tone instruction** from mood × time band,
  using the table in review doc RX-5 (morning soft/encouraging, day hype,
  evening cozy-teasing, late night tired + bedtime needling; bored → more
  heckling, annoyed → short and sarcastic, sleepy → fewer, shorter lines),
  plus **streak awareness**: the last N reaction events (e.g. 3 deaths in a
  row → sympathy → teasing → "want me to look away?"; reset on a win or a
  break).
- **Pass it to felt-core**: felt-tray includes `tone` (felt-animation `GET
  /tone`) as a form/JSON field on `/v1/react/screen`, `/v1/voice-chat`,
  `/v1/text-chat`. felt-core appends it to the system prompt for screen
  reactions and chat (cloud and local). **It isn't personal data**, so it's
  fine for the cloud.
- **Reaction table** (`reactions.json`, data): event → weighted list of
  `{face, tag?, prop?, speak?: bool}`, with mood multipliers and
  repeat-avoidance. Events for now: `screen_reaction(emotion)`, `idle_micro`,
  `reply(emotion)`. Later WPs add `music_*`, `game_*`, `window_*`, `afk_*`.
  Most rows are **non-verbal** (face + body); speech is the exception.
- **Ambient loop** weights now scale with mood (bored → wander/look_around;
  low energy → sit/sleepy).
- Resting face (WP-12) follows mood.

**Tests**: pure functions for drift, event nudges, tone text for sample
states/times, table selection with the seeded RNG and repeat-avoidance.

**Accept**: at different times of day and moods (force the state via a debug
endpoint `POST /mood/debug`), reaction lines audibly change tone, and the
resting face and ambient choices shift.

### Notes from implementation (2026-09-23)

**mood.py**: `MoodState` (clock-injectable like presence.py/hush.py - a
monotonic `now_fn` for elapsed-time drift math, a separate wall-clock
`clock_fn` for hour/date) holds the five-axis vector and a `tick()` that
applies all three drifts (energy toward an hour-keyed target curve on a
20-min time constant; boredom rising 0->1 over ~45 idle minutes;
annoyance decaying on a 30-min time constant) plus the once-per-day
partial reset (annoyance wiped, boredom eased, happiness pulled toward a
baseline; affection deliberately left untouched - it's the slow
relationship axis, not a daily transient). Persisted to
`%APPDATA%\Felt\mood.json` via plain load/save functions (same shape as
wardrobe.py's own), written on every mood-changing event, `POST
/mood/debug`, and every 30s by a new `mood_tick_loop`. **Deliberate scope
cut**: elapsed time for drift is the process's own monotonic clock, not a
persisted wall-clock timestamp - a restart does NOT fast-forward
boredom/annoyance across however long felt-animation was closed. "She was
bored while the app wasn't running" isn't a real feeling to model, and the
daily reset already covers the overnight case without it.

**"Long AFK +boredom"**: no AFK detector exists anywhere in the codebase
yet (RX-3 lists `GetLastInputInfo` as a later signal, not built). Not
faked - boredom's own drift ("rises with no events... for a while") already
covers "nothing has happened in a while" without needing a dedicated
AFK signal; real AFK detection is a natural input to feed it later, not a
prerequisite for the drift itself to work.

**tone.py**: `build_tone_line(mood, hour, streak)` - RX-5's four time-band
baseline lines, plus mood-threshold modifiers (annoyed/sleepy/bored/happy,
checked in that order since annoyed is the strongest override per the
WP's own text), plus streak escalation. **Streak is read off consecutive
sad/annoyed vs. happy/excited reaction emotions**, not an invented "death
detector" - there's no game-event/death signal anywhere in the system, so
this is the honest signal that actually exists (felt-core's X-Emotion
values), matching the WP's own "sympathy -> teasing -> 'want me to look
away?'" escalation shape.

**The tone passthrough (felt-tray/felt-dashboard -> felt-core)**: added
`GET /tone` to felt-animation. felt-tray's Python fetches it (best-effort,
1s timeout, None on any failure - never blocks or fails a turn) before
`/v1/voice-chat` (app.py) and before `/v1/react/screen` and its
felt-vision-fallback `/v1/context/screen` (watcher.py). felt-dashboard's
TS does the same before `/v1/voice-chat` and `/v1/text-chat` (its own
in-window mic/typed-chat paths, which never go through felt-tray's
Python at all - missed on a first pass if only felt-tray were touched).
felt-core threads `tone: str | None` through `chat()` /
`process_screen_context()` / `react_to_screen()` down to every
`_PERSONALITY_PROMPT` use site (a new `_personality_prompt(tone)` helper
replaces the bare constant everywhere), for both the cloud and local
reply paths. `/v1/context/screen` wasn't named in the WP's own endpoint
list (only react/screen, voice-chat, text-chat were) but got the same
treatment anyway since it's the exact same "screen reaction" functionally
(felt-vision's older per-frame fallback path) - leaving it out would have
meant the tone line silently disappearing the moment `/v1/react/screen`
hit a cloud 503, which felt like an oversight rather than a real scope
line.

**Reaction table**: implemented narrower than the WP's own `{face, tag?,
prop?, speak?: bool}` shape - `reactions.json` entries are `{pose, weight,
mood_boost?}` only. No `tag`/`prop`/`speak` fields: felt-animation already
has a separate, working mechanism for which body-tag plays and whether a
reply speaks (`_resolve_reaction_tag`/`hush.active` in server.py) -
duplicating that inside the reaction table would have meant two competing
systems deciding the same thing. What the table actually adds on top,
which didn't exist before: mood-weighted, repeat-avoiding *pose* selection
(`reaction_table.pick_reaction`, same no-immediate-repeat spirit as
face_life.py's `pick_micro_expression`). Two events wired, both real: the
WP's `idle_micro` (replaces face_life_loop's flat random pick when the
table has entries, falls back to the old picker otherwise) and a unified
`reply:<emotion>` (covers both `screen_reaction(emotion)` and
`reply(emotion)` from the WP's text - felt-animation only ever learns an
emotion one way, via `/reply_ready`'s new optional `emotion` field, which
felt-tray now forwards from felt-core's X-Emotion header for screen
reactions specifically; plain chat/skill replies still have none, same as
before this WP, and fall back to WP-12's existing tag-keyword pose
mapping). `music_*`/`game_*`/`window_*`/`afk_*` are exactly what the WP's
own text says are later WPs' job, not missing scope here.

**Ambient loop mood scaling**: `_scale_ambient_weights` multiplies the
existing hour-of-day weight dicts (unchanged) - boredom boosts `walk`/
`ambient_action`, low energy (<0.35) boosts `sleepy`/`sit_down`/
`stay_sitting` - rather than replacing them, so a bored 2am still leans
sleepier than a bored 2pm.

**"Resting face follows mood" - interpretation, not a new system**: there
is no standalone "resting face" anywhere in the codebase to hook (WP-12's
per-region hold compositor just eases back to nothing/whatever the base
clip shows once a hold expires - there was never an explicit neutral pose
applied). Building a second, separate "resting pose" mechanism risked
fighting the hold-timer compositor for the same regions. Interpreted this
bullet as: the mood-weighted `idle_micro` picks above (which fire every
5-20s between real reactions) ARE what governs her face most of the time
- boredom/annoyance already bias which micro-expression shows, which in
practice is "the resting face following mood." Flagged here explicitly
rather than left silent, in case Mario disagrees with that read once he
sees it live.

**Verified**: 189 new/changed tests pass across the three touched repos
(felt-animation 184, felt-tray 86, felt-core 244 - net new: 41 mood/tone/
reaction-table unit tests, 5 ambient-scaling tests, 6 felt-tray
api_client/delivery tests, 7 felt-core tone-threading tests).
felt-dashboard's `tsc --noEmit` is clean. **Live-verified against the real
running felt-animation process** (not just unit tests): `GET /tone`
reflects the real current time band; `POST /mood/debug` forces mood and
the very next `/tone` call reflects every mood-modifier line (annoyed +
sleepy + bored all appeared together correctly); mood persists to
`%APPDATA%\Felt\mood.json` across the debug call; three real `/reply_ready`
calls with `emotion=sad` produced the exact "3rd (or more) in a row" streak
line and correctly nudged happiness (+0.03 x 3) and boredom (-0.10 x 3) via
`on_reaction_spoken`, both confirmed by reading mood back through
`/tone` before and after. **Not verified live**: the actual felt-core ->
Gemini/Ollama -> TTS round trip with a real tone line audibly changing a
spoken reply's wording - that needs a configured Gemini key and Mario
listening, exactly the kind of thing that's this WP's own Accept
criterion and out of reach for a headless check.
