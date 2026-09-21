# Task: implement natural animation polish for felt-overlay + felt-animation

## Context: what exists right now

Read this entire section before writing any code — it's the ground truth
for every change below.

### The animation pipeline (end to end)

1. **felt-tray** captures mic audio, fires `POST /request_started` to
   felt-animation, sends audio to felt-core, gets reply+TTS back, fires
   `POST /reply_ready` (multipart: `text`, `animation_tag`, `audio` WAV)
   to felt-animation.
2. **felt-animation** (`F:\workspace\Projects\felt-animation\`) is a
   FastAPI service on `127.0.0.1:8421`. It owns the overlay process,
   maintains a persistent TCP connection to it, runs Rhubarb lipsync,
   classifies reactions via local Ollama, and enforces the "never
   interrupt" state machine. Key files:
   - `src/felt_animation/server.py` — FastAPI routes + ambient loop
   - `src/felt_animation/state.py` — BehaviorState (activity lock,
     thinking loop, sequence runner)
   - `src/felt_animation/overlay.py` — OverlayClient (persistent TCP,
     play_and_wait with real completion signals)
   - `src/felt_animation/reaction.py` — local Ollama reaction classifier
   - `src/felt_animation/lipsync.py` — Rhubarb subprocess wrapper
   - `src/felt_animation/library.py` — filesystem tag scanner
3. **felt-overlay** (`F:\workspace\Projects\felt-character-assets\felt-godot-overlay\main.gd`)
   is a Godot 4.7 transparent overlay. TCP server on `127.0.0.1:8765`.
   Loads 99 `.vrma` clips into an `AnimationLibrary` named `"official"`.
   Plays tags, sends `{"finished": "<tag>"}` back when one-shot clips end.

### What `_play_tag()` does today (main.gd line 737)

```gdscript
func _play_tag(tag: String) -> void:
    if not tag_to_clips.has(tag):
        push_warning("No clips loaded for tag '" + tag + "'")
        return
    var clips: Array = tag_to_clips[tag]
    if clips.is_empty():
        return
    var clip_id: String = clips[randi() % clips.size()]
    var anim_player: AnimationPlayer = character.get_node_or_null("AnimationPlayer") if character else null
    if anim_player == null:
        return
    anim_player.play("official/" + clip_id)
    print("Tag '", tag, "' -> playing '", clip_id, "'")
```

Key facts:
- `anim_player.play()` is called with **no `custom_blend` argument** →
  zero crossfade, hard skeleton snap on every transition.
- Picks uniformly at random from the tag's clip pool — no history, can
  repeat the same clip back-to-back.
- No AnimationTree exists, only a bare AnimationPlayer.

### What `_on_animation_finished()` does (line 763)

```gdscript
func _on_animation_finished(anim_name: StringName) -> void:
    var clip_id := String(anim_name).trim_prefix("official/")
    var tag: String = clip_tags.get(clip_id, "")
    _broadcast_to_relay({"finished": tag})
    if tag != "idle":
        _play_tag("idle")
```

- Always falls back to bare `"idle"` regardless of posture.
- Broadcasts `{"finished": "<tag>"}` to all TCP peers.

### How lipsync works today (lines 582-640)

Rhubarb cues arrive as `{"lipsync": [{"start": 0.05, "value": "B"}, ...]}`.
In `_process()`:
```gdscript
if _lipsync_start_time >= 0.0:
    _lipsync_current_time += delta
    var current_shape = "X"
    for item in _lipsync_data:
        if _lipsync_current_time >= item["start"]:
            current_shape = item["value"]
    _apply_lipsync_blend(RHUBARB_TO_VRM.get(current_shape, {}))
```

`_apply_lipsync_blend()` **zeros ALL mouth blend shapes**, then **slams**
the target to full weight. No interpolation. Scans
`character.find_children("*", "MeshInstance3D")` every single frame.

### Loop modes

- `idle` tag → `Animation.LOOP_LINEAR` (never fires `animation_finished`)
- Everything else → `Animation.LOOP_NONE` (one-shot, fires on completion)

### The 99-clip library (selected relevant tags)

```
idle/                     — 11 standing idle clips (breathing_idle, female_idle, happy_idle, idle, idle_1, look_around, neutral_idle, standing_idle, standing_idle_1, talking_on_phone, dwarf_idle)
idle/sitting/             — 4 clips (sitting, sitting_1, sitting_2, sitting_idle)
gesture/thinking/         — 1 clip (thinking)
gesture/talking/          — 4 clips (sitting_talking, talking, talking_1, talking_2)
gesture/wave/             — 3 clips (cheering, waving, waving_gesture)
gesture/shrug/            — 3 clips
gesture/clap/             — 3 clips (clapping, sitting_clap, sitting_clap_1)
gesture/point/            — 3 clips
emotion/happy/            — 3 clips (excited, happy, happy_hand_gesture)
emotion/angry/            — 7 clips (angry, angry_gesture, etc., including 3 sitting variants)
emotion/sad/              — 2 clips (crying, rejected)
emotion/scared/           — 2 clips (scared, terrified)
emotion/surprised/        — 2 clips (reacting, surprised)
emotion/embarrassed/      — 1 clip (bashful)
agreement/yes/            — 4 clips
agreement/no/             — 2 clips
sleepy/                   — 4 clips (arm_stretching, batter_on_deck, neck_stretching, yawn)
locomotion/walk/          — 25 clips (includes female_start_walking, stop_walking, female_stop_walking, normal_walk, running, left_turn, right_turn, etc.)
transition/sit_to_stand/  — 1 clip
transition/stand_to_sit/  — 1 clip
dance/                    — 1 clip (salsa_dancing)
reaction/weather/         — 3 generic + 4 sub-tag clips
reaction/failure/         — 1 clip (defeat)
greeting/                 — 1 clip (standing_greeting)
unsorted/                 — 3 clips
```

### Ambient loop today (server.py line 57)

```python
async def ambient_loop() -> None:
    while True:
        await asyncio.sleep(AMBIENT_CHECK_INTERVAL)   # 15s
        if state.busy:
            continue
        if random.random() >= AMBIENT_WANDER_CHANCE:   # 0.2
            continue
        # flat random between walk and sit
        ...
```

### TCP protocol (main.gd ↔ felt-animation)

Inbound (Python→Godot): `{"tag": "..."}\n`, `{"move": {"x": ...}}\n`,
`{"lipsync": [...]}\n`
Outbound (Godot→Python): `{"finished": "<tag>"}\n`

---

## Changes to implement

This is 6 separable features. Implement them in exactly this order
because later ones depend on earlier ones. **Do not skip or reorder.**
Test each one before moving to the next.

---

### Change 1: Crossfade blending on all animation transitions

**Files:** `main.gd` only.

**What:** Add a `custom_blend` duration to every `anim_player.play()`
call so skeleton poses interpolate smoothly instead of snapping.

**How — step by step:**

1. Add a blend-time lookup table near the top of main.gd, after the
   existing `tag_to_clips` dictionary (around line 290):

```gdscript
# Per-tag-category blend time (seconds) for crossfading into a clip from
# that category. Looked up by the INCOMING clip's tag prefix. Falls back
# to DEFAULT_BLEND for unrecognized tags.
const DEFAULT_BLEND := 0.25
const TAG_BLEND_TIMES := {
    "idle": 0.3,
    "locomotion": 0.35,
    "gesture": 0.2,
    "emotion": 0.2,
    "reaction": 0.15,
    "transition": 0.1,
    "dance": 0.25,
    "sleepy": 0.3,
    "greeting": 0.2,
    "agreement": 0.15,
}

func _get_blend_time(tag: String) -> float:
    for prefix in TAG_BLEND_TIMES:
        if tag.begins_with(prefix):
            return TAG_BLEND_TIMES[prefix]
    return DEFAULT_BLEND
```

2. Change `_play_tag()` to use it:

```gdscript
func _play_tag(tag: String) -> void:
    if not tag_to_clips.has(tag):
        push_warning("No clips loaded for tag '" + tag + "'")
        return
    var clips: Array = tag_to_clips[tag]
    if clips.is_empty():
        return
    var clip_id: String = clips[randi() % clips.size()]
    var anim_player: AnimationPlayer = character.get_node_or_null("AnimationPlayer") if character else null
    if anim_player == null:
        return
    var blend := _get_blend_time(tag)
    anim_player.play("official/" + clip_id, blend)
    print("Tag '", tag, "' -> playing '", clip_id, "' (blend=", blend, "s)")
```

The second argument to Godot's `AnimationPlayer.play()` is
`custom_blend: float` — a linear bone-transform interpolation over that
duration. No AnimationTree needed.

**Acceptance:** play two different tags back to back (e.g. idle then
gesture/wave then idle) and confirm visually that the character smoothly
transitions between poses instead of snapping.

---

### Change 2: Smooth lipsync interpolation + cached mesh lookups

**Files:** `main.gd` only.

**What:** Replace the stepped, zero-everything-then-slam lipsync with
smooth per-frame lerping. Cache `MeshInstance3D` references at startup.

**How — step by step:**

1. Add new state variables after the existing lipsync vars (near line
   582):

```gdscript
# Cached blend shape mesh references - populated once in _cache_mouth_meshes()
var _mouth_meshes: Array = []  # [{mesh: MeshInstance3D, shapes: {name: idx}}]

# Smoothly-tracked mouth weights for lipsync interpolation
var _current_mouth_weights: Dictionary = {}  # shape_name -> current float weight
const MOUTH_LERP_SPEED := 14.0

func _cache_mouth_meshes() -> void:
    _mouth_meshes.clear()
    if not character:
        return
    var names_to_find := ["aa", "ih", "ou", "ee", "oh",
        "a", "i", "u", "e", "o", "A", "I", "U", "E", "O",
        "Fcl_MTH_A", "Fcl_MTH_I", "Fcl_MTH_U", "Fcl_MTH_E", "Fcl_MTH_O"]
    for child in character.find_children("*", "MeshInstance3D"):
        var shapes := {}
        for bs_name in names_to_find:
            var idx = child.find_blend_shape_by_name(bs_name)
            if idx != -1:
                shapes[bs_name] = idx
        if not shapes.is_empty():
            _mouth_meshes.append({"mesh": child, "shapes": shapes})
```

2. Call `_cache_mouth_meshes()` at the end of `_build_scene()`, right
   after `_tune_mtoon_materials(character)` (line 526):

```gdscript
    _tune_mtoon_materials(character)
    _cache_mouth_meshes()
```

3. Replace `_apply_lipsync_blend()` entirely with a smooth version:

```gdscript
func _apply_lipsync_blend_smooth(target_weights: Dictionary, delta: float) -> void:
    # Decay all tracked shapes toward 0, rise active ones toward target
    for shape_name in _current_mouth_weights.keys():
        var target_val: float = target_weights.get(shape_name, 0.0)
        _current_mouth_weights[shape_name] = lerp(_current_mouth_weights[shape_name], target_val, MOUTH_LERP_SPEED * delta)
        if abs(_current_mouth_weights[shape_name]) < 0.001 and target_val == 0.0:
            _current_mouth_weights.erase(shape_name)

    for shape_name in target_weights:
        if not _current_mouth_weights.has(shape_name):
            _current_mouth_weights[shape_name] = 0.0
        _current_mouth_weights[shape_name] = lerp(_current_mouth_weights[shape_name], target_weights[shape_name], MOUTH_LERP_SPEED * delta)

    # Apply to cached meshes
    for entry in _mouth_meshes:
        var mesh: MeshInstance3D = entry["mesh"]
        var shapes: Dictionary = entry["shapes"]
        for bs_name in shapes:
            var idx: int = shapes[bs_name]
            var weight: float = _current_mouth_weights.get(bs_name, 0.0)
            # Also check uppercase / Fcl_ variants
            if weight == 0.0:
                for alt in [bs_name.to_lower(), bs_name.to_upper(), "Fcl_MTH_" + bs_name.to_upper()]:
                    if _current_mouth_weights.has(alt):
                        weight = _current_mouth_weights[alt]
                        break
            mesh.set_blend_shape_value(idx, weight)
```

4. Update the lipsync section in `_process()` to call the smooth version
   and pass `delta`:

```gdscript
    if _lipsync_start_time >= 0.0:
        _lipsync_current_time += delta
        var current_shape = "X"
        for item in _lipsync_data:
            if _lipsync_current_time >= item["start"]:
                current_shape = item["value"]
        _apply_lipsync_blend_smooth(RHUBARB_TO_VRM.get(current_shape, {}), delta)
```

5. Delete the old `_apply_lipsync_blend()` function entirely.

**Acceptance:** trigger a voice reply with real TTS audio. Her mouth
should move smoothly between shapes, not snap between them.

---

### Change 3: Automatic blinking

**Files:** `main.gd` only.

**What:** Add a procedural blink cycle — the character currently never
blinks, which is deeply uncanny.

**How — step by step:**

1. Add blink state variables after the mouth cache vars:

```gdscript
# --- Procedural blinking ---
var _blink_timer: float = 0.0
var _blink_next_at: float = 3.0  # first blink after 3s
var _blink_phase: float = -1.0   # -1 = not blinking, 0..1 = blink progress
const BLINK_DURATION := 0.15     # seconds for a full close-open cycle
var _blink_double: bool = false
var _blink_double_done: bool = false

# Cached blink blend shape indices
var _blink_shapes: Array = []  # [{mesh: MeshInstance3D, idx_l: int, idx_r: int}]

func _cache_blink_shapes() -> void:
    _blink_shapes.clear()
    if not character:
        return
    # VRM blend shape names for eye close - try multiple conventions
    var left_names := ["Fcl_EYE_Close_L", "eyeBlinkLeft", "Blink_L", "blink_l"]
    var right_names := ["Fcl_EYE_Close_R", "eyeBlinkRight", "Blink_R", "blink_r"]
    for child in character.find_children("*", "MeshInstance3D"):
        var idx_l := -1
        var idx_r := -1
        for n in left_names:
            idx_l = child.find_blend_shape_by_name(n)
            if idx_l != -1:
                break
        for n in right_names:
            idx_r = child.find_blend_shape_by_name(n)
            if idx_r != -1:
                break
        if idx_l != -1 or idx_r != -1:
            _blink_shapes.append({"mesh": child, "idx_l": idx_l, "idx_r": idx_r})

func _process_blink(delta: float) -> void:
    _blink_timer += delta

    if _blink_phase >= 0.0:
        # Currently in a blink
        _blink_phase += delta / BLINK_DURATION
        # Triangle wave: 0->1 is close, 1->2 is open
        var weight: float
        if _blink_phase < 1.0:
            weight = _blink_phase  # closing
        elif _blink_phase < 2.0:
            weight = 2.0 - _blink_phase  # opening
        else:
            weight = 0.0
            # Check for double-blink
            if _blink_double and not _blink_double_done:
                _blink_phase = 0.0
                _blink_double_done = true
            else:
                _blink_phase = -1.0
                _blink_timer = 0.0
                _blink_next_at = randf_range(2.5, 6.0)
                _blink_double = randf() < 0.15
                _blink_double_done = false

        for entry in _blink_shapes:
            var mesh: MeshInstance3D = entry["mesh"]
            if entry["idx_l"] != -1:
                mesh.set_blend_shape_value(entry["idx_l"], weight)
            if entry["idx_r"] != -1:
                mesh.set_blend_shape_value(entry["idx_r"], weight)
    elif _blink_timer >= _blink_next_at:
        _blink_phase = 0.0
```

2. Call `_cache_blink_shapes()` right after `_cache_mouth_meshes()` in
   `_build_scene()`.

3. Call `_process_blink(delta)` at the end of `_process()`.

**Acceptance:** watch the overlay for 10+ seconds without triggering any
animation. She should blink every few seconds. Occasionally a
double-blink.

---

### Change 4: Idle clip rotation with recent-history avoidance

**Files:** `main.gd` only.

**What:** Stop picking the same idle clip back-to-back. Track recent
history and exclude the last N clips from the pool.

**How:**

1. Add state tracking:

```gdscript
var _recent_clips: Array[String] = []
const RECENT_CLIP_MEMORY := 3
```

2. Replace the random selection in `_play_tag()`:

```gdscript
func _play_tag(tag: String) -> void:
    if not tag_to_clips.has(tag):
        push_warning("No clips loaded for tag '" + tag + "'")
        return
    var clips: Array = tag_to_clips[tag]
    if clips.is_empty():
        return

    # Avoid recently-played clips (mainly for idle variety)
    var candidates: Array = []
    for c in clips:
        if c not in _recent_clips:
            candidates.append(c)
    if candidates.is_empty():
        candidates = clips  # all exhausted, reset

    var clip_id: String = candidates[randi() % candidates.size()]

    # Track history
    _recent_clips.append(clip_id)
    if _recent_clips.size() > RECENT_CLIP_MEMORY:
        _recent_clips.pop_front()

    var anim_player: AnimationPlayer = character.get_node_or_null("AnimationPlayer") if character else null
    if anim_player == null:
        return
    var blend := _get_blend_time(tag)
    anim_player.play("official/" + clip_id, blend)
    print("Tag '", tag, "' -> playing '", clip_id, "' (blend=", blend, "s)")
```

**Acceptance:** watch her cycle through idles for a minute. She should
never play the same idle twice in a row, and you should see at least 4
different idle clips.

---

### Change 5: Expression commands + emotion-driven faces

**Files:** `main.gd` (TCP handler, expression state, expression
application) AND `felt-animation/server.py` (send expression alongside
tag).

#### Part A — Godot side (main.gd)

1. Add expression state vars:

```gdscript
# --- Facial expressions (beyond lipsync) ---
var _expression_targets: Dictionary = {}    # preset_name -> target_weight
var _expression_current: Dictionary = {}    # preset_name -> current_weight
var _expression_decay_timer: float = -1.0   # countdown to start fading expression
const EXPRESSION_LERP_SPEED := 6.0
const EXPRESSION_HOLD_SECONDS := 3.0       # hold expression after clip ends
const EXPRESSION_FADE_SECONDS := 1.5       # fade duration back to neutral

var _expression_shapes: Array = []  # [{mesh: MeshInstance3D, presets: {name: idx}}]

func _cache_expression_shapes() -> void:
    _expression_shapes.clear()
    if not character:
        return
    # VRM expression preset names - try common conventions
    var preset_names := [
        "happy", "angry", "sad", "surprised", "relaxed",
        "Fcl_ALL_Joy", "Fcl_ALL_Angry", "Fcl_ALL_Sorrow", "Fcl_ALL_Surprised",
        "Fcl_ALL_Fun",
        "Joy", "Angry", "Sorrow", "Surprised", "Fun",
    ]
    for child in character.find_children("*", "MeshInstance3D"):
        var presets := {}
        for p in preset_names:
            var idx = child.find_blend_shape_by_name(p)
            if idx != -1:
                presets[p] = idx
        if not presets.is_empty():
            _expression_shapes.append({"mesh": child, "presets": presets})

func _process_expressions(delta: float) -> void:
    # Handle decay timer
    if _expression_decay_timer > 0.0:
        _expression_decay_timer -= delta
        if _expression_decay_timer <= 0.0:
            # Start fading all expressions to zero
            _expression_targets.clear()
            _expression_decay_timer = -1.0

    # Lerp current toward target
    for name in _expression_current.keys():
        var target_val: float = _expression_targets.get(name, 0.0)
        _expression_current[name] = lerp(_expression_current[name], target_val, EXPRESSION_LERP_SPEED * delta)
        if abs(_expression_current[name]) < 0.005 and target_val == 0.0:
            _expression_current.erase(name)

    for name in _expression_targets:
        if not _expression_current.has(name):
            _expression_current[name] = 0.0
        _expression_current[name] = lerp(_expression_current[name], _expression_targets[name], EXPRESSION_LERP_SPEED * delta)

    # Apply to meshes
    for entry in _expression_shapes:
        var mesh: MeshInstance3D = entry["mesh"]
        var presets: Dictionary = entry["presets"]
        for p in presets:
            mesh.set_blend_shape_value(presets[p], _expression_current.get(p, 0.0))
```

2. Call `_cache_expression_shapes()` after blink cache in
   `_build_scene()`.

3. Call `_process_expressions(delta)` at the end of `_process()`.

4. Extend `_handle_tag_line()` to accept `{"expression": {...}}`:

```gdscript
    if parsed.has("expression"):
        _expression_targets = {}
        var expr: Dictionary = parsed["expression"]
        for key in expr:
            _expression_targets[key] = float(expr[key])
        _expression_decay_timer = -1.0  # don't decay while explicitly set
```

5. In `_on_animation_finished()`, start the expression decay timer when
   a reaction clip ends:

```gdscript
func _on_animation_finished(anim_name: StringName) -> void:
    var clip_id := String(anim_name).trim_prefix("official/")
    var tag: String = clip_tags.get(clip_id, "")
    _broadcast_to_relay({"finished": tag})
    if tag != "idle":
        # Start expression decay — hold for a few seconds, then fade
        _expression_decay_timer = EXPRESSION_HOLD_SECONDS
        _play_tag("idle")
```

#### Part B — felt-animation side (server.py + overlay.py)

1. Add an `expression()` method to `OverlayClient` in `overlay.py`:

```python
    async def expression(self, weights: dict[str, float]) -> None:
        await self.send({"expression": weights})
```

2. Add a tag-to-expression mapping in `server.py`:

```python
TAG_EXPRESSIONS: dict[str, dict[str, float]] = {
    "emotion/happy": {"happy": 0.9, "Fcl_ALL_Joy": 0.9, "Joy": 0.9},
    "emotion/angry": {"angry": 0.8, "Fcl_ALL_Angry": 0.8, "Angry": 0.8},
    "emotion/sad": {"sad": 0.7, "Fcl_ALL_Sorrow": 0.7, "Sorrow": 0.7},
    "emotion/scared": {"surprised": 0.6, "Fcl_ALL_Surprised": 0.6, "Surprised": 0.6},
    "emotion/surprised": {"surprised": 0.9, "Fcl_ALL_Surprised": 0.9, "Surprised": 0.9},
    "emotion/embarrassed": {"sad": 0.3, "Fcl_ALL_Sorrow": 0.3},
    "gesture/thinking": {"sad": 0.15, "Fcl_ALL_Sorrow": 0.15},
    "greeting": {"happy": 0.5, "Fcl_ALL_Joy": 0.5, "Joy": 0.5},
    "gesture/wave": {"happy": 0.6, "Fcl_ALL_Joy": 0.6, "Joy": 0.6},
    "dance": {"happy": 1.0, "Fcl_ALL_Joy": 1.0, "Joy": 1.0},
}
```

3. In `_handle_reply()`, send the expression command right before the
   reaction sequence plays:

```python
async def _handle_reply(text: str, animation_tag: str | None, audio_bytes: bytes) -> None:
    # ... (existing lipsync + classify logic) ...

    await state.end_thinking_and_wait()

    tags_to_play: list[str] = []
    resolved_tag, needs_stand_up = library.resolve_posture_tag(animation_tag, state.posture, known_tags)
    if needs_stand_up:
        # ... (existing stand-up logic) ...

    tags_to_play.append(resolved_tag)

    # Send facial expression for the reaction
    expr = TAG_EXPRESSIONS.get(resolved_tag)
    if expr is None:
        # Try prefix match
        for prefix, weights in TAG_EXPRESSIONS.items():
            if resolved_tag.startswith(prefix):
                expr = weights
                break
    if expr:
        await overlay.expression(expr)

    await state.run_sequence(tags_to_play, CLIP_TIMEOUT)
```

**Acceptance:** trigger a reply that classifies as `emotion/happy`. Her
face should visibly change (smile/joy blend shape). After the clip ends,
the expression should hold for ~3 seconds, then smoothly fade back to
neutral over ~1.5 seconds.

---

### Change 6: Richer ambient behavior with time-of-day awareness

**Files:** `felt-animation/server.py` only.

**What:** Replace the flat 20%-walk-or-sit ambient loop with a weighted
state machine that varies by current posture and time of day.

**How:**

Replace the entire `ambient_loop()` function:

```python
import datetime

AMBIENT_MIN_INTERVAL = 20.0   # minimum seconds between ambient actions
AMBIENT_MAX_INTERVAL = 45.0   # maximum


async def ambient_loop() -> None:
    while True:
        interval = random.uniform(AMBIENT_MIN_INTERVAL, AMBIENT_MAX_INTERVAL)
        await asyncio.sleep(interval)
        if state.busy:
            continue

        hour = datetime.datetime.now().hour

        if state.posture == "sitting":
            await _ambient_sitting(hour)
        else:
            await _ambient_standing(hour)


async def _ambient_standing(hour: int) -> None:
    # Late night: bias toward sleepy actions
    if 23 <= hour or hour < 6:
        weights = {
            "idle_variety": 40,
            "sleepy": 35,
            "walk": 10,
            "sit_down": 10,
            "surprise": 5,
        }
    else:
        weights = {
            "idle_variety": 50,
            "walk": 20,
            "sleepy": 8,
            "sit_down": 12,
            "look_around": 5,
            "surprise": 5,
        }

    action = _weighted_choice(weights)

    if action == "idle_variety":
        # Just replay idle — the clip-rotation in main.gd ensures variety
        await overlay.send({"tag": "idle"})

    elif action == "sleepy" and "sleepy" in known_tags:
        await state.run_sequence(["sleepy"], CLIP_TIMEOUT)

    elif action == "walk" and AMBIENT_WALK_TAG in known_tags:
        new_x = random.uniform(-2.0, 2.0)
        await overlay.move(new_x)
        walk_tags = []
        if "locomotion/walk/start_walking" in known_tags or "locomotion/walk/female_start_walking" in known_tags:
            start_tag = "locomotion/walk/female_start_walking" if "locomotion/walk/female_start_walking" in known_tags else "locomotion/walk/start_walking"
            walk_tags.append(start_tag)
        walk_tags.append(AMBIENT_WALK_TAG)
        if "locomotion/walk/stop_walking" in known_tags or "locomotion/walk/female_stop_walking" in known_tags:
            stop_tag = "locomotion/walk/female_stop_walking" if "locomotion/walk/female_stop_walking" in known_tags else "locomotion/walk/stop_walking"
            walk_tags.append(stop_tag)
        await state.run_sequence(walk_tags, CLIP_TIMEOUT)

    elif action == "sit_down":
        if "transition/stand_to_sit" in known_tags and "idle/sitting" in known_tags:
            await state.run_sequence(["transition/stand_to_sit"], CLIP_TIMEOUT)
            state.posture = "sitting"
            await overlay.send({"tag": "idle/sitting"})

    elif action == "look_around" and "idle" in known_tags:
        # look_around is one of the idle clips — it'll be picked by rotation
        await overlay.send({"tag": "idle"})

    elif action == "surprise":
        surprises = [t for t in ["dance", "greeting", "unsorted"] if t in known_tags]
        if surprises:
            await state.run_sequence([random.choice(surprises)], CLIP_TIMEOUT)


async def _ambient_sitting(hour: int) -> None:
    weights = {
        "stay_sitting": 50,
        "stand_up": 35,
        "sleepy": 15 if (23 <= hour or hour < 6) else 5,
    }
    action = _weighted_choice(weights)

    if action == "stay_sitting" and "idle/sitting" in known_tags:
        await overlay.send({"tag": "idle/sitting"})

    elif action == "stand_up":
        if "transition/sit_to_stand" in known_tags:
            await state.run_sequence(["transition/sit_to_stand"], CLIP_TIMEOUT)
        state.posture = "standing"
        await overlay.send({"tag": "idle"})

    elif action == "sleepy" and "sleepy" in known_tags:
        # Stand up first, play sleepy, then back to standing idle
        if "transition/sit_to_stand" in known_tags:
            await state.run_sequence(["transition/sit_to_stand"], CLIP_TIMEOUT)
        state.posture = "standing"
        await state.run_sequence(["sleepy"], CLIP_TIMEOUT)


def _weighted_choice(weights: dict[str, int]) -> str:
    total = sum(weights.values())
    r = random.randint(1, total)
    cumulative = 0
    for action, weight in weights.items():
        cumulative += weight
        if r <= cumulative:
            return action
    return list(weights.keys())[-1]
```

Remove the old `AMBIENT_CHECK_INTERVAL` and `AMBIENT_WANDER_CHANCE`
constants, they're replaced by the min/max interval + per-action weights.

**Acceptance:** leave the overlay running for 5+ minutes with no voice
input. She should:
- Cycle through different idle poses (not the same one)
- Occasionally walk (with smooth start/stop if those clips exist)
- Occasionally sit down and stand back up
- If tested after 11pm, she should yawn/stretch noticeably more often

---

## Files touched — complete list

| File | Changes |
|------|---------|
| `F:\workspace\Projects\felt-character-assets\felt-godot-overlay\main.gd` | Changes 1-5a (crossfade, lipsync, blink, clip history, expressions, TCP expression handler) |
| `F:\workspace\Projects\felt-animation\src\felt_animation\server.py` | Changes 5b, 6 (expression mapping + ambient rewrite) |
| `F:\workspace\Projects\felt-animation\src\felt_animation\overlay.py` | Change 5b (add `expression()` method) |

No new files. No new dependencies. No protocol-breaking changes (all new
TCP fields are additive — existing `{"tag":...}` and `{"finished":...}`
are unchanged).

## Definition of done

1. Watch her idle for 30 seconds — she blinks, transitions between
   different idle clips with smooth crossfades, never snaps.
2. Trigger a voice chat — thinking plays with smooth blend-in, reply
   reaction plays with smooth blend-in, her face changes with the
   emotion, the expression lingers and fades after the clip ends.
3. Watch lipsync during a voice reply — mouth moves smoothly between
   shapes, no popping.
4. Leave her alone for 5 minutes — she walks (with start/stop clips),
   sits down, stands up, yawns (if late), cycles through idle variety.
5. No regressions: the existing `{"tag": ...}` protocol still works,
   `{"finished": ...}` still fires, the state machine still enforces
   "never interrupt."
