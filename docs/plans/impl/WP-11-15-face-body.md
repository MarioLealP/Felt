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
