# Phase 5 — Assets and the desktop world (WP-18 … WP-23)

Read `00-implementer-context.md` first. One WP per session. These are bigger
and more exploratory than phases 1–4. Each one says where a decision or a
check with Mario is needed.

---

## WP-18

### Animation assets: Animset Pro triage + downloads + proper walking
**Repos**: `E:\Felt\Animations` (library, via felt-character-assets),
AnimToVrmaConverter (tools), felt-animation + main.gd (walking). **Size**: M.
**Depends on**: WP-01.

**Part A: triage the owned Movement Animset Pro clips (no production
needed).** 208 `.vrma` files already sit loose in `E:\Felt\AnimToVrmaConverter\`
(`MovementAnimsetPro_*.vrma`). Copy the useful ones into library tag folders
(folder = tag):

| Tag folder | Clips (names without the `MovementAnimsetPro_` prefix) |
|---|---|
| `locomotion/turn/left90`, `…/right90`, `…/left180`, `…/right180` | `TurnLt90_Loop`, `TurnRt90_Loop`, `TurnLt180`, `TurnRt180` |
| `locomotion/walk/start` | `WalkFwdStart` |
| `locomotion/walk/start_turn90_left` / `_right` / `start_turn180_*` | `WalkFwdStart90_L/R`, `WalkFwdStart180_L/R` |
| `locomotion/walk/stop` | `WalkFwdStop_LU`, `WalkFwdStop_RU` |
| `locomotion/run/start`, `…/stop` | `RunFwdStart`, `RunFwdStop_LU/RU` |
| `air/jump_start` | `JumpIdleStart` |
| `air/fall` | `FallingLoop` |
| `air/land_soft` / `air/land_hard` | `JumpIdleLand` / `JumpIdleLandHard` |
| `climb/1m`, `climb/2m`, `climb/vault` | `RunStrafeUpdate_Climb1m`, `SlideClimb_Climb2m`, `SlideClimb_Vault1m` |
| `recover/getup_back`, `recover/getup_face` | `RunStrafeUpdate_GetUpFromBack`, `…FromFace` |
| `crouch/idle`, `crouch/enter`, `crouch/exit` | `Crouch_Idle`, `Idle2Crouch`, `Crouch2Idle` |
| `prop/pickup_right`, `prop/pickup_left` | `PickUp_RH`, `PickUp_LH` |
| `prop/throw_right`, `prop/throw_left` | `ThrowAway_RH`, `ThrowAway_LH` |
| `prop/kick` | `RunStrafeUpdate_KickTrashcan` |
| `gesture/button_push`, `gesture/keypad` | `ButtonPush_RH`, `KeypadUse_RH` (the "working" pose) |
| `reaction/turn_surprised` | `RunStrafeUpdate_Turn180Surprised` |
| `gesture/dont_know` | `DontKnow` |
| `sit/chair_start`, `sit/chair_loop`, `sit/chair_end` | `RunStrafeUpdate_SitChair{Start,Loop,End}` |

Skip the fighting, lever, door, strafe and patrol sets. **Keep her existing
feminine walk** (`locomotion/walk/normal_walk`) as the main walk cycle; the
Animset Pro gait is generic/masculine. Check each copied clip in the overlay
(number-key test mode, or send `{"tag": …}` by socket), because retargeting
issues show up per clip. Drop broken ones and list them in the notes. Don't
commit the paid `.unitypackage` anywhere.

**Part B: downloads** (pre-approved by Mario; "we have lots of space and more
variety is good"):
- **Quaternius Universal Animation Library 1 + 2** (CC0; quaternius.com / itch).
  FBX/GLB on a universal humanoid rig. Convert with the existing FBX → VRMA
  path (`Convert-MixamoFbx.ps1` / `Convert-MixamoBatch.ps1` are generic FBX
  converters despite the name). Unity Humanoid auto-mapping should take the
  UAL rig; confirm on one clip first.
- **Bandai Namco Research Motion Dataset** (GitHub, BVH, **non-commercial**
  licence, which is fine for Felt). It's valuable for **styled** variants
  (tired, happy, active walks) for mood-driven locomotion. BVH → FBX via the
  Blender leg of `Generate-Animation.ps1`, then → VRMA.
- **VRoid official VRMA pack**: **already downloaded** at
  `F:\workspace\Vroid\Animations\VRMA_MotionPack`. Some of its clips
  ("Show full body", "Greeting", "Peace sign", "Model Pose") are already in
  the library. Check which of the 7 aren't yet, and add them. They're native
  `.vrma`, so they drop straight in.
- Keep a `CREDITS.md` in the library root (source, licence, per pack).
- Tag new clips into existing folders where they fit (idle variety, emotions,
  gestures) and new ones where useful (`locomotion/walk/happy`,
  `…/tired`, `…/sneak`).

**Part C: walking that looks like walking** (review doc A-4). Today
`character.position.x` exponentially `lerp`s toward `_target_x`: fast start,
slow crawl, feet skating, and no turning, so she walks facing the camera while
sliding.
- main.gd:
  - `move_toward` at a **constant speed** matched to the walk clip (measure
    the stride: distance/second at which the feet don't slide; ~1.2–1.4 m/s
    scaled to the rig; run ~2×);
  - rotate her about **70° toward the travel direction** over ~0.25 s before
    stepping and back to facing the camera on arrival;
  - send `{"arrived": true}` over the relay when she reaches the target.
- felt-animation:
  - the walk sequence becomes turn (the new turn clips) → `walk/start` → loop
    `normal_walk` **until `arrived`** (replaces the random 2–4 repeats) →
    `walk/stop` → turn back;
  - speed and gait variant follow mood (WP-15) when styled walks exist.

**Accept**: she turns, walks at a steady pace with planted feet, stops and
faces the camera. The new clips play without retarget glitches. `CREDITS.md`
exists.

### Notes from implementation (2026-09-24) — resolved via `Update Felt.bat`

**Update**: Mario pointed at `E:\Felt\Update Felt.bat` (`UpdateFelt.ps1`) -
the project's own real `--export-release` pipeline, distinct from the ad-hoc
`--editor --quit-after N` headless pass used below to diagnose this. Running
it did a full clean import + export and **the "Failed to find required VRM
keys" error did not recur at all** - all 36 new clips came through cleanly
(`Storing File: .../*.vrma.import` for every one of them, zero VRM errors in
the export log). Live-verified after the export: sent `climb/1m` and
`locomotion/turn/left90` directly over the relay socket and screenshotted -
both show clearly correct, distinct poses (a 90° side turn; a forward-leaning,
knees-bent reach with her back to the camera for the climb) - conclusively
different from a flat idle stand, unlike every earlier attempt. The root
cause below was correctly diagnosed as a real gap in the ad-hoc headless
import path; it turned out the project's own proper export flow doesn't hit
it (likely because a full `--export-release` does a genuinely clean
reimport pass the partial runs below didn't). **Not fully re-verified
per-clip** - only spot-checked 2 of 36 after the fix; the rest are presumed
good given the mechanism is now confirmed working, but a Mario visual pass
before leaning on all of them (e.g. in WP-18C) is still the safer bet.

**Original diagnosis (superseded above, kept for the record):**

- Copied all 36 tag folders' worth of clips (38 files - `locomotion/walk/stop`
  and `locomotion/run/stop` each get two variants) from
  `E:\Felt\AnimToVrmaConverter\MovementAnimsetPro_*.vrma` into
  `felt-character-assets/felt-godot-overlay/animations/library/<tag>/`,
  exactly per the WP's own mapping table. Every source file the table names
  exists and was copied correctly - verified filename-by-filename before
  copying.
- **Live-testing them surfaced something bigger than "check each clip, drop
  the broken ones":** the running FeltOverlay.exe is an EXPORTED build - its
  `res://` resources are baked in at export time, so it can never see newly
  added loose `.vrma` files no matter how many times felt-animation (or the
  exe itself) restarts. Confirmed by checking `export_presets.cfg` (no
  include/exclude filters - the whole project is baked into the exe, no
  loose-file asset folder alongside it) and `build/windows/` (no `.pck`, no
  loose animations dir). This is a durable fact about how this project's
  asset pipeline works that's worth flagging for any future WP that adds new
  animation/asset files: **testing new assets needs the live Godot editor
  binary** (`E:\Felt\felt-character-assets\tools\godot\Godot.exe --path
  felt-godot-overlay`), same as the standing rule for testing new main.gd
  *code* - it wasn't previously written down that this applies to new
  *assets* too, not just script changes.
- Switched to running the live editor binary directly. It immediately
  surfaced the real problem: **every one of the 36 new clips fails to
  import**, with `ERROR: [VRM][ERROR][vrm_extension.gd] Failed to find
  required VRM keys in json`, and consequently `No loader found for
  resource: ... (expected type: unknown)` at runtime (no `.import` file ever
  gets generated because the import step itself fails).
- **Root cause, traced to the actual line**: `addons/vrm/importer/v1/
  vrm_animation_export.gd:282`'s `add_vrm_nodes_to_skin_v0()` looks for
  `extensions.VRM.humanoid` (the legacy VRM 0.x avatar-description key) in
  every `.vrma` file, regardless of which VRM spec version the file actually
  uses. But **every `.vrma` in this project - the 36 new ones AND the
  already-working ones alike - only declares `extensions.VRMC_vrm_animation`**
  (confirmed byte-for-byte: `extensionsUsed":["VRMC_vrm_animation"]` in both
  a new file and `gesture/wave/goodbye.vrma`, an existing working clip; the
  legacy `"VRM":{` key is absent from both). By this code's own logic, the
  already-working clips should ALSO fail this exact check today - the
  working evidence is that they don't fail in practice, which means they're
  not actually being re-validated through this code path at all; they're
  running off `.import` cache files generated at some earlier point (as this
  addon's own comments reference "Godot 4.6 bug" workarounds, hinting the
  addon itself has changed since those were generated). **This is a bug in
  the project's current VRM-animation import path, not a per-clip
  retargeting problem** - it would block ANY brand-new `.vrma` file added to
  this project right now, not just this batch, and it isn't something a
  "drop the broken ones" pass can work around, since (per the evidence)
  literally all of them are broken.
- Did not attempt to fix `add_vrm_nodes_to_skin_v0`/the addon itself - this
  is custom-modified third-party addon code (not something built this
  session) that Mario has context on and should weigh in on the right fix
  for (patch the v0 path to also accept `VRMC_vrm_animation`'s own
  `humanoid.humanBones` shape? force new imports through a different
  importer? something else?), rather than a blind fix from someone without
  that history.
- Left the copied files in place (`git status` will show them as new,
  untracked) - they're correct, harmless, and become immediately usable
  once the import bug is fixed; deleting them and redoing the copy later
  would be pure waste.

**Part C (walking that looks like walking) - built, live-verified:**

- `BehaviorState.walk_to` (felt-animation) replaces the old fixed "2-4
  repeats" (`_build_walk_tags`, WP-10) - start clip -> loop the cycle clip
  until main.gd's real `{"arrived": true}` notice -> stop clip, holding the
  activity lock throughout. All 5 places that used to build a fixed-repeat
  walk sequence (ambient wander, presence walk-off/walk-on, shoo, come-here)
  now share this one path via a `_walk_to` helper.
- main.gd: `move_toward` at a constant `WALK_SPEED_MPS`/`RUN_SPEED_MPS`
  (1.3/2.6 m/s, the WP's own numbers) replaces the exponential lerp, plus a
  turn-out/step/turn-back state machine - a 70 partial turn toward the
  travel direction over 0.25s before stepping, back to 0 (facing camera) on
  arrival, broadcasting `{"arrived": true}` for real.
- `overlay.wait_for_arrived` mirrors `play_and_wait`'s real-completion-
  signal pattern (not a guessed duration); `move()` gained a `running` flag.
- **Four real bugs found and fixed live** (Mario caught the third one in
  real time: "she is facing away from me"):
  1. The walk cycle clip and idle were fighting each other's blend on every
     single repeat - `_on_animation_finished`'s auto-revert-to-idle fired
     the instant a cycle clip finished (local, zero latency) before
     felt-animation's next loop iteration could re-send the same tag over
     the network, so idle and the walk clip kept interrupting each other's
     0.3s blend before either ever finished transitioning - visibly
     corrupting the pose (limbs/hair reading as detached from a coherent
     body). Fixed by giving `locomotion` tags the same auto-revert
     exemption `idle` already had, since felt-animation always sends a real
     follow-up tag during an active walk anyway.
  2. The turn-back-to-camera rotation was being silently overwritten by the
     walk cycle clip's own root rotation track, because the walk state
     machine ran from `_process()`, with no guarantee it ran after the
     AnimationPlayer's own update that frame - the *exact* ordering bug
     `_clamp_feet_to_floor`/nod/gaze/beat-bob already had to work around
     (see `_ready()`'s own comments). First fix attempt: moved to
     `get_tree().process_frame`, same as those. **Looked fixed in testing,
     wasn't** - see #3.
  3. Mario reported her facing away live, after #2's fix. Traced it further:
     `locomotion/walk/start` and `locomotion/walk/stop` (two of Part A's
     newly retargeted MovementAnimsetPro clips) turned out to play facing
     ~180 away from the camera **on their own**, confirmed by sending each
     in isolation with zero rotation code involved - a bad retarget in the
     source clips themselves (exactly the "drop broken ones" case Part A's
     own text warned about), not a logic bug. Even `locomotion/walk/
     normal_walk` (pre-existing, previously assumed fine, never actually
     exercised long enough for anyone to notice before this WP's constant-
     speed rewrite) showed the same symptom in isolation. felt-animation
     stopped playing the two broken transition clips; separately, and more
     fundamentally, main.gd now runs the whole walk system on a
     `_character_pivot` wrapper node above `character` that no animation
     clip's own root track can ever touch - the walk system owns world
     position/facing outright now, rather than sharing `character`'s own
     transform with whatever a clip's retarget happens to bake into it.
     This is the fix that actually held up under repeat testing, not #2's
     ordering fix alone (which only fixed *when* a value won a given frame,
     not a clip re-asserting a *different* value later).
  4. Found while stress-testing #3's fix (rapid back-to-back walk triggers
     overlapping with a `call_lively` signal reaction): a **transient**
     mesh-fragmentation glitch (limbs/hair briefly reading as detached,
     same visual signature as #1) that self-resolved within a few seconds
     without getting stuck. Lower priority than the other three - not
     reported by Mario, only found by deliberately hammering it harder than
     normal use would - flagged here rather than silently left, not
     chased further this session.
- **Live-verified against the real exported build** (via `Update Felt.bat` -
  the ad-hoc headless `--editor --quit-after N` import path used earlier in
  this WP does NOT reflect what actually ships, learned the hard way): a
  real walk-to-cursor turns, walks with a visibly cycling stride (screenshots
  showed genuinely different mid-stride leg positions across frames, not a
  static pose), arrives, and turns back to face the camera reliably across
  repeated triggers - matching the WP's own Accept criterion, screenshotted
  at each stage including the pivot-node fix specifically.
- **Not verified**: run-speed specifically (never triggered a `running=True`
  walk live this session - the 0.3-probability run branch in the ambient
  loop just didn't happen to fire during testing), and the "styled walks
  follow mood" bullet (no styled walk variants exist yet - that's Part B).

**Part B (external downloads) not started this session**: no longer blocked
by the import bug, but still a bigger, separate asset-sourcing effort
(downloading/converting third-party packs, licensing/CREDITS.md tracking) -
not started, left for a dedicated pass.

**Screenshot testing tooling**: found and used the existing
`{"screenshot": "<name>"}` relay message (main.gd's `_schedule_screenshot`,
saves to `E:/Felt/scratch/<name>.png`) to drive a scripted per-tag capture
pass. Left the 36 captured PNGs in `E:/Felt/scratch/` (all show the same
un-crouched/un-turned idle pose across every new tag, now understood to be
because none of them ever actually loaded - not evidence of a retargeting
problem on their own, now that the real cause is known).

### Notes from implementation: Part B (2026-09-26)

**Result: 58 clips added (32 Quaternius UAL, 26 Bandai Namco), 0 from the
VRoid pack; 1 clip dropped (VRoid Squat).** No existing clip was moved or
renamed. felt-animation, main.gd and felt-core are untouched: the new tags
exist but nothing picks them yet (mood-styled walk selection is a separate
step).

- **VRoid VRMA pack**: 6 of the 7 are already in the library (byte-identical
  md5): `Show full body`, `Greeting`, `Peace sign`, `Finger Gun` (VRMA_04
  "Shoot"), `Spin`, `Model Pose`. Only **VRMA_07 "Squat"** was missing. I
  added it, but it's **dropped as broken**: in the overlay it never squats.
  She stands straight with her arms held out sideways at the moments the
  hips track dips (3.4 s, 6.9 s). Cause: VRMA_07's rest pose uses rotated
  bone frames (hips rest quaternion `[0.5,0.5,0.5,0.5]`, limbs along X),
  unlike VRMA_01–06 (identity rests), and main.gd's retarget doesn't handle
  that. Fixable later by re-baking it to identity rests (world-delta
  conversion) if Mario wants it.
- **Quaternius UAL 1 + 2**: only the **free "Standard" tier** exists without
  paying (43 takes each; the Pro/Source zips are paid). It was fetched from
  itch.io without a login. Each pack is one multi-take FBX, and
  `Convert-MixamoFbx`/`BatchMixamoConverter` only take the first clip
  (`A_TPose`), so I added `MultiClipFbxConverter.cs` (one `.vrma` per take).
  **Rig mapping was confirmed on one clip first** (`Walk_Formal_Loop`):
  Unity auto-mapped every humanoid bone (pelvis→Hips, spine_01→Spine,
  spine_02→Chest, thigh/calf/foot/ball, clavicle/upperarm/lowerarm/hand,
  fingers). But the rig came out **facing ~180° away** (hips yaw +166…-177°
  where known-good clips read 0°). Unity's clip root settings
  (rotationOffset, bake-into-pose) turned out to be ignored by
  AnimationClipToVrmaCore (identical output, tested), so
  `vrma_fix_facing.py --yaw 180` rewrites the hips track. After it the
  clip faced the viewer in the overlay. Then batch: 32 useful takes
  (weapons, swimming, farming, sword/shield, death and slide were skipped).
- **Bandai Namco dataset-1** (dataset-2 wasn't needed): the walks are
  5–16 s straight-line takes (stand, walk ~8 m, stop), and the BVH rest pose
  isn't a T-pose (every chain lies along +X). New tools:
  - `bvh_cycle.py` cuts one seamless in-place gait cycle (seam error
    0.4–1.7° average) and reports the natural speed.
  - `bvh_to_fbx_tpose.py` re-rests the skeleton in a facing-aware T-pose
    and bakes the motion onto it via world-space Copy Transforms. Unity then
    auto-maps all 21 bones.
  - The dataset has **no sneak style**, so `locomotion/walk/sneak` is UAL's
    crouched walk (`Crouch_Fwd_Loop`).
  - Styles renamed for tags: `not-confident`→`shy`, `old`→`elderly`.
  - The two feminine gestures were yawed +39°/+22° to face the viewer.
- **Walk speeds differ from main.gd's 1.3 m/s**. Tired is about 1.0, sad
  0.4–0.6, proud 0.7, happy 1.4 and active 1.5–1.7. The wiring step should
  set the speed per gait, or the feet will slide. The values are in
  `CREDITS.md`.
- **Ledge sit: neither pack has one.** Only UAL's free Standard tier is
  available, and it has chair sits (`Sitting_*`) and a standing rail lean
  (`Idle_Rail_Loop`, now `ambient/lean_rail`). Bandai has no sitting at
  all. WP-23's ledge sit still needs sourcing: felt-t2a-studio ("sits on a
  ledge swinging legs"), a Booth shortlist, or UAL Pro (paid, needs Mario's
  OK). Nothing was invented. **Resolved 2026-09-26:** Mario said to use the
  existing sit animations for the ledge instead (see WP-23).
- **`.pck` size**: 376,325,604 → 377,801,664 bytes (+1.48 MB, +0.4 %).
- The `Failed to find required VRM keys` error prints twice per new `.vrma`
  during export (from the v0 preflight in `vrm_extension.gd`). It's
  **harmless**: every such clip got its `.import`, loaded, and played.

**New tags**:
- `locomotion/walk/{happy,tired,sad,angry,feminine,childish,proud,active,shy,elderly,formal,sneak,carry,zombie}`
- `locomotion/jog`
- `greeting/bow`
- `emotion/annoyed`
- `ambient/{fixing,lean_rail,phone_call,snack}`
- `reaction/hit`
- `prop/{chest_open,pickup_table}`

Clips were also added to these existing tags:
- `idle`, `idle/sitting`
- `transition/{stand_to_sit,sit_to_stand}`
- `gesture/{talking,talking/sitting,button_push,shaking_head,nodding,wave}`
- `dance`
- `air/{jump_start,fall,land_soft}`
- `crouch/idle`, `climb/1m`, `recover/getup_back`, `prop/throw_right`

The full per-clip list is in `CREDITS.md`.

### Proof

- **Files**:
  - 58 `.vrma` + 58 `.vrma.import` under
    `felt-character-assets/felt-godot-overlay/animations/library/`. The
    library has 169 `.vrma` (111 before).
  - `animations/library/CREDITS.md`.
  - Tooling in `E:\Felt\AnimToVrmaConverter\`: `MultiClipFbxConverter.cs`,
    `vrma_fix_facing.py`, `bvh_cycle.py`, `bvh_to_fbx_tpose.py`, plus a
    README section.
- **Commits**:
  - felt-character-assets: `2a0de98` (UAL, 64 files), `d3dedb8` (Bandai,
    52 files) and `da437a4` (CREDITS), pushed `7637990..da437a4 main -> main`.
  - AnimToVrmaConverter: `46d5673`, pushed `b60717f..46d5673`.
- **Conversion**:
  - `MultiClipFbxConverter: done. ok=43 failed=0` for UAL1 and for UAL2.
  - `MultiClipFbxConverter: done. ok=26 failed=0` for Bandai (log
    `E:\Felt\scratch\wp18b\bn_all.log`).
  - `vrma_inspect.py`: hips XZ drift ≤ 0.02 m on every added looping clip
    (no sliding baked in), and hips yaw ≈ 0 at clip start after the fixes.
- **Export**:
  - `..\tools\godot\Godot.exe --headless --export-release "Windows Desktop" build/windows/FeltOverlay.exe`
    reported `export exit=0`.
  - The final export log `E:\Felt\scratch\wp18b\export_final.log` has 116
    `Storing File` lines for `ual1_/ual2_/bn1_` files (58 × `.vrma` + `.import`).
  - The overlay logged `Loaded '…'` 169 times.
- **Per-clip visual check**:
  - A temporary single-clip `wp18b_review/<clip>` tag was built for each of
    the 59 candidates, played by socket on an overlay launched directly
    (felt-animation stopped, so nothing fought her body), and screenshotted
    mid-clip.
  - The overlay log showed 59 `Tag 'wp18b_review/…' -> playing` lines. That
    log was later overwritten by the final spot-check run.
  - Screenshots are `E:\Felt\scratch\wp18b_<clip>.png`, crops
    `crop_<clip>.png`.
  - The review tags were removed before the final export (0 `wp18b_review`
    lines in `export_final.log`).
- **Gemini review**:
  - 4 batches via `agy-delegate`; raw answers in
    `E:\Felt\scratch\gemini_review_wp18b_{1..4}.txt`.
  - It flagged 6 of 59: Squat, `ual1_hit_chest`, `ual1_hit_head`,
    `bn1_walk_not_confident_001`, `bn1_walk_old_001`, `bn1_bow_feminine`.
    I checked every flag myself (`E:\Felt\scratch\wp18b\m_flagged.png`,
    `m_reshoot.png`):
    - Squat: confirmed broken.
    - The two hit clips (0.3/0.4 s) had simply ended before the capture.
      Re-shot at 0.15/0.2 s they show a small hit flinch, so they're fine.
    - The other 3 are false positives: normal mid-stride walks and a deep
      bow.
  - Random "OK" checks, 3 per pack, all agreed (6/6: `ual1_sitting_enter`,
    `ual2_idle_rail_loop`, `ual2_laytoidle`, `bn1_walk_feminine_002`,
    `bn1_walk_happy_001`, `bn1_byebye_childish`; `m_okcheck.png`).
  - Agreement: 1 of 6 flags was a real defect, 0 misses in the sample.
- **Final build spot check** (normal tags, `m_final.png`):
  - Tags checked: `locomotion/walk/happy`, `…/tired`, `…/sneak`,
    `greeting/bow`, `emotion/annoyed`, `ambient/lean_rail`. All face the
    viewer and are posed correctly.
  - Raw log: `Tag 'locomotion/walk/happy' -> playing 'bn1_walk_happy_002' (blend=0.35s)`.
- **Left running**:
  - felt-animation restarted hidden (PID 35728 listening on :8421).
  - It relaunched the overlay (PID 27168 on :8765), and the relay
    connection is `Established` between them.
- **No `.vrm`/`.vrm.import` touched**: none is newer than this session's
  first download. The untracked `characters/Felt_*` outfits are left alone.

### Not done / unverified

- **Ledge-sit clip**: not in either pack (see above). Still open for WP-23.
- **VRoid Squat** dropped (rest-pose mismatch). It isn't in the library.
- **Walking in motion not checked for foot sliding**. Each clip was checked
  from a single frame, plus the hips-drift numbers. No styled walk was
  played while main.gd actually moves her, because nothing sends those tags
  yet. At 1.3 m/s the slow styles will visibly slide until speed is set per
  gait.
- **Loop seams judged numerically only** (bvh_cycle seam error). The
  overlay re-blends each loop anyway.
- **Style choice is based on the source labels.** Mario hasn't judged
  whether `feminine`/`childish`/`shy` read as cute on Felt.
- **UAL clips have a slight hips yaw of about -14° in their idle stances**
  (the UAL rest stance). It looks natural in the screenshots but hasn't been
  judged by Mario.
- Dataset-2 (2,902 more Bandai clips: feminine/youthful walks, waves) wasn't
  used. It's an easy follow-up with the same tools.

### Notes from implementation: walk smoothness fix (2026-09-26)

Mario: "she walks but isn't smooth at all". Diagnosed from a timed capture
(new `{"screenshot": name, "burst": true}` relay message, every ~85 ms
through a `POST /presence action=move` walk), with hip x measured from the
alpha bounding box (scale 157 px/m at half size). Two walks at different
pivot speeds gave the same scale.

**Ranked causes (evidence):**
1. **H2 root motion (main cause).** The clips in use, `walk_forward` and
   `run_forward`, are the only root-motion cycles in the library: the hips
   move forward 1.46 m and 2.31 m per clip (the bn1/UAL styled walks stay
   in place). The pivot moved her as well, so hip x was a sawtooth. Before:
   speed swung from -2.5 to +3.7 m/s (sd 1.79), 9/35 frames went
   *backwards*, 45 cm off a straight line, and she snapped back 0.7 m on
   arrival.
2. **H1 cycle boundary.** The clips pad a **frozen tail**: the whole pose
   holds from 0.80 s (walk) or 0.60 s (run) to 0.967 s. Each cycle was a
   one-shot re-sent over the network (`finished` every 1.02-1.03 s: the
   0.967 s clip plus ~60 ms of latency), with a 0.35 s restart blend. There
   was no random clip switching, since each cycle tag has one clip.
3. **H3 speed mismatch.** Her natural pace (drift / real 0.80 s cycle,
   scaled to her rig) is 1.94 m/s walk and 4.10 m/s run. With the 70° turn,
   that's 1.82 / 3.85 m/s on screen, against a pivot at 1.3 / 2.6. FK on
   the source shows the feet planted (toes hold z=0.24 m, then 1.34 m) and
   hips at a constant 0.061 m/frame, so matching the pace plants the feet.
4. **H4 (gaze/feet clamp/turn) not supported.** The only other periodic
   signal is a smooth, gait-locked head bob, the same before and after.

**Fix:**
- main.gd `_make_in_place_cycle`: for `locomotion` clips that are
  seamless cycles, it trims the frozen tail and removes the hips' net
  horizontal drift linearly, and it records the root speed.
- `_walk_speed`: the pivot moves at that root speed × sin(turn), and falls
  back to 1.3/2.6 for in-place clips.
- The new `{"tag", "loop": true}` loops the clip, but only while a move is
  in progress.
- felt-animation `walk_to` sends the cycle **once**, looping, arms the
  arrived waiter before the move, and just waits for `arrived`.
- main.gd still swaps to idle on arrival. The Part C behaviour (turn-out,
  turn-back, pivot ownership, walk start/stop disabled) is unchanged.

**After** (2 walks): hip speed 1.27-2.32 m/s (sd 0.29), 0 backward frames,
4 cm max off a straight line, no mid-walk `finished`, 2-3 cm settle on
arrival. One 90 ms frozen frame in the second walk didn't line up with
anything in the log and isn't periodic (likely the capture).

**Not done:** `run/start` and `run/stop` (runs only) still carry 1.1-1.7 m
of root motion while the pivot is still, so a run still lurches forward and
slides back at its start and stop. Not verified live for runs.

**Follow-up, same day: "she strides always with the same leg".** The
source cycle is lopsided, and it was before this fix too (the same clip
data; the old restarts and foot sliding hid it). FK on `walk_forward`: the
right foot works -0.28..+0.48 m around the hips, the left -0.57..+0.10, so
the steps alternate 1.10 m (right) and 0.36 m (left). The 0.80 s trim is
the real cycle (the pose at 0.80 = the pose at 0 within 0.04°), and the
legs are half a cycle apart; the drift strip only moved the hips linearly.
In the overlay, the planted-shoe positions gave steps of 0.41 / 1.07 /
0.39 / 1.06 m. `run_forward` is milder (right -0.42..+0.54, left
-0.54..+0.35, hips yawed +13..+30°).
- **Fix (option a):** main.gd `_symmetrise_cycle` runs on the root-motion
  cycles. It rebuilds each Left bone as the mirrored Right bone half a cycle
  later (rest-relative deltas in skeleton space, across the plane between
  the upper legs). Centre bones and the hips position meet their mirrored
  half-shift halfway. The right side is the template because its foot stays
  closer under the hips (mean +0.10 m vs -0.24).
- **After:** steps 0.81 / 0.65 / 0.80 / 0.66 m. The remaining ±0.07 m is
  the feet's ±0.074 m lateral offset seen at the 70° turn (±0.05 m on
  screen). Hip speed is 1.39-2.68 m/s, with 0 backward frames. Run poses
  were checked by montage only (the test run lasted 0.8 s).
- **Why not option b:** among the symmetric Bandai/UAL walks, `active_001`,
  `active_002` and `tired_002` have single-frame glitches (60°, 180° and
  30° jumps). `formal` walks with stiff arms. `childish_002` is clean but
  strongly styled. All of them are in place, and main.gd doesn't know their
  pace yet (CREDITS.md speeds). **The default walk is still
  `locomotion/walk/normal_walk` (`walk_forward`), now symmetrised.**

**Follow-up 2: "her feet are at a 30º incline".** This was caused by the
symmetrise template. A new `{"probe_bones"}` debug message reads each
foot's rotation against its rest pose in-engine. Mid-stance foot pitch
while walking (+ = toes down):
- original clip: left +4.3°, right **-38.6°** (right heel stance, roll
  +9°; the raw .vrma already has it);
- right-side template (5238e4f): left -32.5°, right -34.6° (roll ±13°),
  which is Mario's 30°;
- idle feet: within 1°.

`run_forward`'s right foot is also rolled +58° at mid-stance. The left
side is the good one in both clips, so `_symmetrise_cycle` now rebuilds
Right from mirrored Left. **After:** walking mid-stance left +3.1°,
right +3.6° (roll ±2.6°); run in place +2.7° / -0.1°. Steps are an even
0.71-0.74 m (ratio 0.97), planted-foot slip is 0.13 m/s, and hip speed
never goes backwards. The default walk is still `normal_walk`.

---

## WP-19

### Sound batch: non-verbal vocalisations + filler lines, in *her* voice
**Repos**: new tooling under `E:\Felt\tools\sounds\` (umbrella),
felt-voice on the Nitro5 (read-only use of its RVC code), felt-animation
(playback hooks). **Size**: M. **Depends on**: none (WP-08 for the playback
hook).

**Rule**: one voice. Every sound must go through the **same RVC Teto model**
felt-voice uses (`src/felt_voice/rvc.py`, `FELT_VOICE_RVC_MODEL_PATH` on the
Nitro5).

1. **Non-verbals: generate with Orpheus TTS**, whose inline tags are `<laugh>
   <chuckle> <sigh> <cough> <sniffle> <groan> <yawn> <gasp>`. Prompts like
   "mm <yawn>", "<chuckle> okay", "hm? <gasp>". Generate 3–5 takes each for:
   giggle, laugh, sigh, yawn, gasp, "hm?", "mm-hm", "ooh", "ugh", "hehe".
   - **Where**:
     - **Nitro5 (RTX 3060 6 GB, CUDA)**: fair game to stop Ollama/ComfyUI
       for the batch (restore them after).
     - **Desktop (AMD RX 6700, no CUDA)**: a GGUF-quantized Orpheus under
       llama.cpp (Vulkan) with the small SNAC decoder on CPU.

     Pick whichever works first and note why.
2. **Filler / presence lines**: plain Piper + RVC through felt-voice's normal
   `/v1/tts` ("hmm", "one sec", "let me see", "ooh, okay", "back!", "okay
   okay, I'll zip it", "rude!"). A few takes each via different punctuation or
   speed.
3. **Re-voice the Orpheus takes** through RVC. Add a small script on the
   Nitro5 that imports felt-voice's RVC module and converts a folder of WAVs.
   **Don't modify the running felt-voice service**; if a new endpoint is
   genuinely cleaner, discuss it first.
4. **Curate**: put everything in `E:\Felt\Sounds\candidates\<kind>\`. Build a
   tiny local HTML page (open it in Mario's **local Firefox**, not an
   artifact) with a player per file and keep/reject buttons that download a
   JSON of the keepers. **Mario picks by ear.** Move the keepers to
   `E:\Felt\Sounds\<kind>\`.
5. **Hook up** (felt-animation): `sounds.json` maps tag → sound kind
   (`sleepy/yawn` → yawn, `emotion/laughing` → giggle/laugh,
   `emotion/sighing` → sigh, `air/land_hard` → "ugh", surprise → gasp).
   Play at clip start through `audio.py` (WP-08; respects ducking and hush:
   non-verbals are allowed during hush at a lower gain, per Mario's
   never-quiet spirit; note it). Fillers: play one if a prompted request hasn't
   answered within ~1.5 s (`/request_started` + timer), or immediately for
   known-slow skills.

**Accept**: Mario approved a keeper set; yawns, giggles and sighs play in sync
with their clips in her voice; the filler fires on slow requests.

### Notes from implementation (2026-09-25, restart from step 1)

Restarted from step 1 after the audit. Decisions made since the spec
(these override it): the primary non-verbal generator is **full
Chatterbox** (Mario: "run the giggle, chuckle etc through the full non
turbo"), with Orpheus as a secondary for comparison. Chatterbox-Turbo tags
are out ("horrendous"). Every candidate ends in the live RVC Teto model,
revoiced two ways.

**Stopped at Mario's curation. No keepers have been picked.** Open
`E:\Felt\Sounds\candidates\curate.html` in local Firefox, then run
`uv run python E:\Felt\tools\sounds\apply_keepers.py <decisions.json>`.

What was done:

- **Generators.**
  - Full Chatterbox ran on the Nitro5 in `~/felt-voice-next`, as a
    separate process with the `bench_full.py` low-VRAM split. Sounds were
    written phonetically, 4 spellings per kind × exaggeration 0.7/0.9,
    cfg_weight 0.5/0.3 alternating, a distinct seed per take, and T3
    capped at 150 speech tokens. Takes that trimmed to outside 0.25–3.0 s
    were retried with a new seed.
  - Orpheus 3B (`hf.co/unsloth/orpheus-3b-0.1-ft-GGUF:Q4_K_M`) ran
    through the Nitro5's existing Ollama (CUDA) in raw mode, with the SNAC
    24 kHz decoder on CPU. **Why the Nitro5 and not the desktop:** Ollama
    with CUDA was already there, and the pull plus the raw prompt worked
    on the first try (~92 tok/s). The desktop Vulkan llama.cpp in
    `tools/llamacpp/` wasn't needed and wasn't touched.
    - Prompt: `<custom_token_3><|begin_of_text|>{voice}: {text}<|eot_id|><custom_token_4><custom_token_5><custom_token_1>`,
      stop at `<custom_token_2>`.
    - Voices tara, leah and zoe; native tags `<laugh> <chuckle> <sigh>
      <yawn> <gasp> <groan>`.
    - Orpheus has no `<giggle>` tag, so giggle and hehe use "hehehe
      <chuckle>"-style prompts. hm, mm-hm and ooh use plain text.
    - Up to 4 takes per kind within 0.25–3.0 s (4.0 s for yawns, which
      run long).
- **RVC.** `nitro/revoice_ab.py` writes to a new folder and never
  overwrites its input (the old `~/felt-voice/revoice_batch.py` is
  untouched and unused).
  - A = the live `rvc.py` params: rmvpe+, index 0.66, protect 0.33.
  - For B I tried three breath-preserving variants, all with protect
    0.5: rmvpe+ at index 0.33, crepe at index 0.33, and crepe at index 0.
  - **B = crepe, index 0.33, protect 0.5.** It turned the fewest sounds
    into words by Whisper (table below). Index 0 was worse than 0.33. The
    rmvpe+ B and crepe index-0 files stay on the Nitro5 only
    (`~/felt-voice-next/wp19/out/rvc/*_rvcB.wav`, `*_rvcBc0.wav`); they're
    not on the page.
- **Fillers and presence** were regenerated through the live `/v1/tts`
  (Turbo → RVC, plain POSTs, nothing changed on the service).
  `presence` is now its own kind: `back_*`, `zip_it_*`, `rude_*`. The 15
  old Piper-voice fillers were moved (not deleted) to
  `E:\Felt\Sounds\candidates\_old_piper\`. "hmm" got 6 takes instead of
  3, because Turbo plus RVC keeps turning a bare "Hmm" into a word.
- **Curation page.** `build_curation_page.py` was rewritten.
  - Per kind, each take is one row with its source, prompt text and
    generator settings, plus an RVC A player and an RVC B player side by
    side. Each player has Keep/Reject, its Whisper transcript (an orange
    "words" flag when Whisper heard real words), and what Whisper heard
    before RVC.
  - "Download decisions.json" keeps the `{"kind/file.wav": "keep"|"reject"}`
    format, so `apply_keepers.py` is unchanged.
  - Decisions persist in localStorage. `_`-prefixed folders are skipped.
- **Step-5 code fixes (felt-animation):**
  - `17a3ab1`: sound effects play on a separate `sfx_player`. An effect
    is skipped while reply speech plays, and speech/repeat stops any
    effect first, so a tagged reply's clip sound can no longer cut off
    her sentence. Call ducking drives both players. The hush gain (0.3)
    is applied per effect, so the speech gain is never touched.
  - `31f2247`:
    - The presence kind: "back!" on `_walk_onscreen(greet=True)` (the
      away timer), "zip it" on `/hush` (played just before the hush
      starts, so the acknowledgement is at normal volume), and "rude!"
      not wired (WP-23).
    - `pick_filler_path` reads `filler/` only and also ignores stray
      `back_/zip_it_/rude_` files there.
    - `sounds.json` values can be a list of kinds.
  - `1f6d9b8` + `2d821c6`: `sounds.json` is tracked.
    - `emotion/laughing` → laugh or giggle at random, among the kinds
      that have keepers.
    - `sleepy/yawn` → yawn, `emotion/sighing` → sigh, `air/land_hard` →
      ugh, `emotion/surprised` and `reaction/turn_surprised` → gasp.
    - `FELT_SOUNDS_DIR` is in `.env.example`.
    - `2d821c6` fixes invalid JSON escaping in the first commit's comment.
    - Pushed.
- **Scripts** are all in `E:\Felt\tools\sounds\` (Nitro5 ones under
  `nitro\`; copies run from `~/felt-voice-next/wp19/`):
  - `chatterbox_nonverbals.py`
  - `orpheus_gen.py` (non-verbals + the speech timing test)
  - `revoice_ab.py`
  - `gen_fillers.py`
  - `stt_check.py`
  - `assemble_candidates.py`
  - `wp19_audio.py` (trim + RVC settings)
- **Round-3 speech A/B (Turbo vs Orpheus), skipped per Mario's rule.**
  3 warm lines took 11.6–12.7 s each for 7.8–8.1 s of audio, against
  Turbo's 2.4–3.2 s for the same lines. Details are in Proof.

### Proof

**Files** (`E:\Felt\Sounds\candidates\`, counted after copying):

- 284 candidates: giggle 22, laugh 24, chuckle 24, hehe 24, sigh 24,
  yawn 22, gasp 24, hm 24, mm-hm 24, ooh 24, ugh 24, filler 15,
  presence 9.
- `_old_piper\` holds 15 files.
- `manifest.json` covers all 284 ("0 without metadata").

| kind | Chatterbox takes | Orpheus takes | files (×2 RVC) |
|---|---|---|---|
| giggle | 8 | 3 | 22 |
| laugh, chuckle, hehe, sigh, gasp, hm, mm-hm, ooh, ugh | 8 each | 4 each | 24 each |
| yawn | 8 | 3 | 22 |
| **total** | **88** | **42** | **260** + 15 filler + 9 presence |

**Commands and raw output:**

```
# full Chatterbox (Nitro5; qwen2.5:3b unloaded, ComfyUI stopped)
uv run --no-sync python wp19/chatterbox_nonverbals.py wp19/out/raw_cb giggle
{"generated": 8, "rejected": 0, "gen_median_s": 1.17, "total_s": 31.9, "torch_max_allocated_mib": 1670}
uv run --no-sync python wp19/chatterbox_nonverbals.py wp19/out/raw_cb laugh chuckle hehe sigh yawn gasp hm mm-hm ooh ugh
  reject hehe_cb09_s4 attempt 0 (0.16s)
{"generated": 81, "rejected": 1, "gen_median_s": 1.15, "total_s": 109.5, "torch_max_allocated_mib": 1668}

# Orpheus non-verbals
uv run --no-sync python wp19/orpheus_gen.py nonverbals wp19/out/raw_orph
laugh_orph_1: leah '<laugh>' 0.52s (113 tok in 1.21s)   ... total 139.1s
(yawn rerun with the 4 s limit) yawn_orph_1: tara '<yawn>' 2.82s (232 tok in 2.51s) ... total 31.0s
find wp19/out/raw_orph -name '*.wav' | wc -l  -> 42 ; raw_cb -> 88

# RVC, 130 raw takes x 4 settings
uv run --no-sync python wp19/revoice_ab.py wp19/out/rvc A,B,Bc wp19/out/raw_cb wp19/out/raw_orph
{"files_in": 130, "settings": ["A", "B", "Bc"], "median_s_per_file": {"A": 0.976, "B": 0.985, "Bc": 1.447}, "total_s": 453.7}
{"files_in": 130, "settings": ["Bc0"], "median_s_per_file": {"Bc0": 1.283}, "total_s": 170.6}

# fillers via the live /v1/tts
filler/hmm_1: 'Hmm.' HTTP 200 ... 1.3-1.7 s each; 24 x "HTTP 200"
```

**Whisper spot check** (live `/v1/stt`, base.en). The count is takes where
the transcript contains real words, by `stt_check.py`'s heuristic:

| | raw (before RVC) | A (live) | B rmvpe+ | **B crepe (used)** | crepe idx 0 |
|---|---|---|---|---|---|
| Chatterbox, all 88 | 46 | 70 | 66 | 65 | 66 |
| Orpheus, all 42 | **6** | 30 | 27 | **21** | 27 |
| laugh/giggle/chuckle/hehe, Chatterbox 32 | 17 | 29 | 27 | 23 | 25 |
| laugh/giggle/chuckle/hehe, Orpheus 15 | 3 | 13 | 12 | 9 | 11 |

Raw examples:

- Orpheus `hehe_orph_2`: raw "Heh heh heh heh", A/B/crepe all "See you
  later!". This is the known "laugh → See ya!" failure.
- `chuckle_orph_2`: raw "Heh heh heh", A "The best", crepe "Heh heh heh".
- Chatterbox `giggle_cb09_s2` "hehehe!": raw "Bye bye.", so full
  Chatterbox already speaks words before RVC.

Filler/presence examples: "let me see", "one sec", "ooh okay" and "zip
it" all transcribe correctly. The hmm takes came back as "and", "heh",
"2", "Okay". "Rude" came back as "Road"/"Root", and "back" as
"That"/"But."/"back." Whisper is unreliable on one-word clips, so these
need Mario's ear.

**Orpheus speech timing** (`orpheus_gen.py lines wp19/out/r3 tara O1 3`,
warm; live felt-voice resident, qwen2.5:3b unloaded, ComfyUI stopped):

```
01 {'audio_s': 8.11, 'llm_s': 7.31, 'snac_s': 3.5, 'synth_s': 10.81, 'rvc_s': 1.9, 'total_s': 12.71, 'ttfa_s': 0.65, 'tokens': 666, 'tok_per_s': 92.0}
02 {'audio_s': 7.77, 'llm_s': 7.02, 'snac_s': 3.24, 'synth_s': 10.26, 'rvc_s': 1.33, 'total_s': 11.59, 'ttfa_s': 0.48, 'tokens': 638, 'tok_per_s': 91.4}
03 {'audio_s': 8.02, 'llm_s': 7.28, 'snac_s': 3.31, 'synth_s': 10.58, 'rvc_s': 1.09, 'total_s': 11.68, 'ttfa_s': 0.47, 'tokens': 659, 'tok_per_s': 91.2}
vram_before 2488 peak 5850   (ollama ps: 2.8 GB, 17%/83% CPU/GPU)
```

- Turbo for the same lines: 3.15 / 2.54 / 2.79 s.
- Streaming time-to-first-audio is 0.5–0.65 s, but RVC Teto isn't
  streaming, and ~92 tok/s barely beats real time (~84 tok/s).
- It can't sit next to qwen2.5:3b and the live felt-voice either: the
  card was at 5850/6144 MiB without the chat model.

**felt-animation:**

```
uv run pytest -q   -> 352 passed after 17a3ab1; 363 passed in 2.72s after 31f2247/2d821c6
git push           -> 203dfd9..2d821c6  main -> main
```

**Nitro5 restored** (before the batch: felt-voice 2410 MiB + ComfyUI 110 +
qwen2.5:3b 2200 = 4740 MiB):

```
qwen2.5:1.5b  1.2 GB  100% CPU  4096 ;  qwen2.5:3b  2.2 GB  100% GPU  4096
felt-comfyui active; felt-voice active (same PID 9816, never restarted); ollama active
0 stray wp19 processes; card 4734 MiB
tts HTTP 200 134444 B 1.774287s
```

### Not done / unverified

- **Keepers not picked**: that's Mario, by ear on the page. Nothing is
  in `E:\Felt\Sounds\<kind>\` yet, so no sound plays live.
- **Not heard in sync with clips.** The step-5 fixes are verified by unit
  tests only. The running felt-animation (started 22:27) still has the
  old code. It picks up the fixes on its next restart, and there's
  nothing to hear until keepers exist.
- **Breath preservation is judged by Whisper only**, not by ear. B
  (crepe) is the best of the variants tried, but it still turns roughly
  half the laughs into words. Chatterbox often produces words before RVC
  even runs.
- Orpheus has no giggle tag (the giggle and hehe takes are approximations).
  Only 3 Orpheus yawns and 3 Orpheus giggles passed the length filter.
- Round-3 speech A/B: skipped (too slow, see above). Only 3 lines were
  timed, and no page section was built.
- "Play a filler immediately for known-slow skills" is still not built
  (a pre-existing gap: felt-animation has no signal for which skill
  runs).
- "zip it" plays on any `/hush`, including the keybind. That's a design
  choice, not reviewed by Mario.
- **Left on the Nitro5:**
  - The Orpheus GGUF stays pulled in Ollama (2.1 GB).
  - `snac` 1.2.1 is installed into `~/felt-voice-next/.venv` with
    `uv pip --no-deps`. It's not in that project's `pyproject.toml`, so a
    `uv sync` there would remove it.
  - The raw takes and unused RVC variants are in
    `~/felt-voice-next/wp19/out/`.
- `Sounds/ab-test/` in the umbrella is still untracked. It's from the
  voice A/B work, not WP-19, and was left as is.

---

## WP-20

### AnimationTree layering
**Repo**: felt-character-assets (main.gd). **Size**: L. **Depends on**:
WP-14, WP-18.

**Why**: one `AnimationPlayer.play()` at a time means she can't gesture while
walking or sitting, and every new behaviour fights the others.

**Do**:
- Introduce an `AnimationTree` over the existing `AnimationLibrary`:
  - **Base layer**: two alternating `AnimationNodeAnimation` slots (A/B)
    cross-faded by a blend value. `_play_tag` for base-class tags
    (idle, locomotion, sit, air, climb, recover) loads the chosen clip into
    the inactive slot and fades over the tag's blend time. This keeps the
    tag → random clip selection and repeat-avoidance.
  - **Upper-body layer**: a `Blend2` with a **bone filter** (spine up: chest,
    upperChest, neck, head, shoulders, arms, hands, fingers) fed by its own
    A/B slot pair, for gestures/emotions/talking while the base layer keeps
    walking or sitting. Tag classes decide the layer: `gesture/*`,
    `emotion/*`, `reaction/*` (non-full-body) → upper; the rest → base. Keep
    a per-tag override list for full-body reactions.
  - Procedural layers (gaze WP-14, nods WP-13, beat bob WP-16) stay as
    post-process bone offsets, applied after the tree.
- **Completion signals**: keep `{"finished": tag}` semantics per layer
  (compute from clip length and elapsed time, since AnimationTree doesn't
  emit `animation_finished` the same way). felt-animation's state machine
  depends on them.
- Keep the relay protocol backward compatible.

**Accept**: she can wave while walking and talk-gesture while sitting.
Existing behaviours (thinking loop, reactions, sit/stand, walk) still work,
and finished notices still arrive.

### Notes from implementation (2026-09-26)

**Architecture (main.gd).** An `AnimationTree` (`LayerTree`, a child of the
VRM scene) now plays the same `AnimationLibrary`. The VRM's own
`AnimationPlayer` only holds it and is set inactive.
- **Base layer**: two `AnimationNodeAnimation` slots (A/B), each behind an
  `AnimationNodeTimeSeek` so a newly loaded clip restarts at 0, cross-faded
  by a `Blend2`. A new clip goes into whichever slot shows less, and the
  blend fades toward it over the tag's `TAG_BLEND_TIMES` time.
- **Upper layer**: its own A/B pair, mixed over the base by a `Blend2`.
  Its filter is `Chest` and every bone under it (114 bones: upper chest,
  neck, head, eyes, shoulders, arms, hands, fingers, hair), so hips, spine
  and legs always come from the base.
- **Unchanged**: tag → random clip, repeat-avoidance, looping `idle*`, the
  walk `loop` flag and the in-place/symmetrised cycles. `deterministic` is
  copied from the player (false).
- **Completion**: each layer tracks its clip's elapsed time against its
  length (`_update_layers`, also while she's hidden) and sends
  `{"finished": tag, "layer": "base"|"upper"}`. Looping clips never
  finish.
  - An upper one-shot fades the upper layer out over 0.3 s.
  - A base one-shot reverts to the last idle posture. Locomotion is still
    exempt while a walk is moving.
- **New `"interrupted": true` notice**: a one-shot replaced before it ends
  now sends `{"finished", "interrupted": true}` (the old player sent
  nothing, so waiters sat out the 30 s timeout). It isn't sent when the
  same tag replaces itself, because that clip's own notice answers the
  waiters.

**Tag classes. main.gd decides them and reports them** (`_tag_layer`), sent
as `{"layers": {tag: class}}` to every client on connect. I chose this over
a shared list in the README: which body part a clip uses is presentation,
so there is one source of truth, and felt-animation can't drift from it.
felt-animation only reads the report to pick locks.
- **`upper`**: `gesture/*`, `emotion/*`, `reaction/*`, minus the overrides.
  Played on the upper layer when the base is doing something (walking,
  sitting, a transition) or the upper layer is already in use.
  - While the base is only standing idle they play full body, exactly as
    before WP-20. Their own leg and hip motion is kept, so standing
    gestures look unchanged.
  - If a base-class tag (a walk) starts mid-clip, the clip moves onto the
    upper layer at the same time position: no visible cut, and no finished
    notice until it really ends.
- **`base`**: `idle*`, `locomotion/*`, `sit/chair_loop`, `crouch/idle`.
  These are postures and cycles a gesture rides on; changing them never
  stops an upper clip.
- **`full`**: everything else (transitions, ambient, dance, sleepy, air,
  climb, recover, prop, greeting, greeting/bow) plus the override list.
  They play whole-body on the base layer, and the upper layer fades out.
- **Override list, checked per clip** (lower-body motion measured from the
  `.vrma` tracks: max leg rotation from frame 0, hip rotation and hip
  travel):
  - `reaction/turn_surprised`: 180° hip turn, 0.93 m of travel. **Full.**
  - `reaction/hit`: small (legs ≤ 10°, hips ≤ 9°, 0.02 m), but kept
    full-body as the spec lists it: a hit is a whole-body event. It is a
    one-line change to layer it.
  - `greeting/bow` (hips 14–40°, spine 11–13°) and `recover/*` aren't
    upper-class, so they are full anyway.
  - The other upper tags have a few big-leg clips (`emotion/happy` jump,
    `emotion/angry` just_do_it, `emotion/sad` sad_idle_1, `gesture/wave`
    byebye_happy, `gesture/shaking_head` no). Standing, they play full body
    as before. Layered, only their upper body shows, so they're not
    overrides.

**Procedural layers.** `FeltPoseModifier` is unchanged and still the first
child of `Skeleton3D`. The feet clamp is on the tree's `mixer_applied`. The
frame order is proved by counters in `{"probe_bones"}`: 31,295 modifier
runs in the same frame as, and after, `mixer_applied`, against 2 without
(the first frames at startup).

**felt-animation.**
- `state.py`: the single activity lock became a **base lock** and an
  **upper lock**.
  - `run_sequence` / `begin_thinking` with all-`upper` tags take only the
    upper lock.
  - Any other tag takes base then upper. That is the old behaviour: a
    full-body clip waits for a gesture and never cuts it off. The fixed
    order means no deadlock.
  - `walk_to` takes only the base lock.
  - `busy` still means either lock is held, so the ambient, idle-refresh
    and micro-expression loops behave as before.
  - `run_sequence`, `play_and_wait`, `begin_thinking` and `walk_to` keep
    their semantics.
- `overlay.py`: stores the report (`tag_layer`). A tag missing from it
  counts as `full`, so an old overlay gets the old single-lock behaviour
  (tested).
- `overlay.py` also logs every finished notice with its layer.
  `is_looping_tag` is unchanged (still `idle*`, the same as main.gd's
  `_is_looping_tag`).
- `library.resolve_posture_tag(upper_body=)`: while sitting, an upper-class
  reply tag with no `/sitting` variant now plays over the sitting legs
  instead of standing her up first.
- Relay protocol: additive only (`layers`, and `layer`/`interrupted` on
  `finished`), documented in felt-character-assets/README.md.

### Proof

Test driver `E:\Felt\scratch\wp20\drive.py` (socket, prints every overlay
reply with ms). Hip x comes from `hipx.py`: the centroid of the alpha band
45–58 % down her bounding box, which ignores a waving arm, at 157 px/m for
half-size bursts. Crops are `E:\Felt\scratch\wp20_c_*.png`; montages are
`E:\Felt\scratch\wp20\m_*.png`.

- **Build**: `Godot_console.exe --headless --export-release "Windows
  Desktop" build/windows/FeltOverlay.exe` gave exit 0, pck 377,811,856 B
  (`E:\Felt\scratch\wp20_export.log`). Startup log:
  `WP-20 AnimationTree: base + upper layers, upper mask = Chest and below (114 bones), deterministic=false`.
- **Wave while walking** (`m_wavewalk.png`, overlay driven directly):
  arms up waving, legs mid-stride, position advancing.
  - Probe mid-walk: `base={'clip': 'walk_forward', 'tag': 'locomotion/walk/normal_walk'} upper={'clip': 'bn1_byebye_feminine', 'tag': 'gesture/wave', 'weight': 1.0}`.
  - Hip x: 36 frames, 20 moving, 0 backward while stepping, 0.48–2.41 m/s.
    The one -0.31 m/s frame is the 2.5 cm settle at the turn-back (the
    WP-18 walk had the same 2–3 cm settle).
  - Plain walk without a wave, same metric: 35 frames, 0 backward,
    0.31–2.49 m/s.
- **Wave while walking through felt-animation's own locks**:
  `POST /presence action=move`, then 0.6 s later `POST /debug/play_tag
  gesture/wave`.
  - `F:\Temp\felt-animation.log`:
    `12:10:28,606 playing 'locomotion/walk/normal_walk' (looping)` →
    `12:10:36,416 finished 'gesture/wave' (layer upper)`. The wave was
    sent at 12:10:29, mid-walk, not queued behind it.
  - Hip x: 41 frames, 22 moving, 0 backward, 0.63–2.52 m/s.
- **Talk gesture while sitting** (`m_sittalk.png`): seated legs from
  `idle/sitting`, the upper body from `gesture/talking/sitting` (probe
  `upper={'clip': 'sitting_talking', 'weight': 0.94}` over
  `base={'clip': 'idle_sit'}`). The standing `gesture/talking` clip
  (talking_2) layered over the sit also gestures with seated legs.
- **Full-body reaction interrupting** (`m_interrupt.png`):
  - (a) Wave on the upper layer after a walk, then `reaction/turn_surprised`:
    `{"finished": "gesture/wave", "interrupted": true, "layer": "upper"}`,
    the turn plays whole-body, then
    `{"finished": "reaction/turn_surprised", "layer": "base"}`, and the
    base is back on `idle`.
  - (b) `gesture/talking` playing full body while standing (probe
    `'gesture': True`), then the turn:
    `{"finished": "gesture/talking", "interrupted": true, "layer": "base"}`.
- **Thinking loop during a real `/request_started`**, while walking
  (`m_think.png`): `POST /presence move`, `POST /request_started`, then
  4 s later `POST /reply_ready` (text, `animation_tag=gesture/nodding`,
  1.2 s silent WAV). Log lines:
  - `12:11:07,502 playing 'locomotion/walk/normal_walk' (looping)`
  - `12:11:11,983 finished 'gesture/thinking' (layer upper)`
  - `12:11:16,191 finished 'gesture/thinking' (layer upper)` (the reply
    let the current iteration finish)
  - `sync offset=31.0ms`
  - `12:11:17,870 finished 'gesture/nodding' (layer upper)`

  Legs walking with the head on the up-left thinking glance. The arms are
  `thinking_face` (arms crossed): the same upper body full body vs layered
  in `m_thk.png`.
- **Idle → sit → stand** (`wp20_c_wp20_rt_{0idle,1sitting_down,2sat,3sit_talk,4stood}.png`):
  transitions through `/debug/play_tag` (the lock path), posture tags
  raw, as the ambient loop sends them. Log:
  - `12:12:15,873 finished 'transition/stand_to_sit' (layer base)`
  - `12:12:49,603 finished 'transition/sit_to_stand' (layer base)`

  The final probe is `base={'clip': 'idle01', 'tag': 'idle'}`, standing.
  `sit_to_stand` waited for the seated talk to release the upper lock
  ("never interrupt").
- **Finished notices on both layers** in felt-animation's log since the
  restart: 25 (14 `layer base`, 11 `layer upper`). They include ambient
  ones such as `finished 'emotion/laughing' (layer base)` and
  `(layer upper)`, and `finished 'ambient/fixing' (layer base)`.
- **Gaze + nod over a gesture** (`m_gaze.png`): with the seated talk on the
  upper layer (probe weight 1.0), gaze point x=0.02 turns her head
  hard left and x=0.98 turns it right. The nod dips the top of her head
  2 px (half size) at 0.17 s. The procedural layer is on top of the tree.
- **Gemini review**, 2 batches, 21 crops (`E:\Felt\scratch\wp20\gemini_{1,2}.txt`):
  - 4 flagged, all checked by me and all false positives:
    - `e2ewave_40732`: the far arm occluded mid-stride.
    - `think_80291` / `think_81289`: `thinking_face`'s crossed arms
      foreshortened at the 70° walk turn; confirmed with a full-resolution
      reshot and a full-body vs layered comparison.
    - `rt_3sit_talk`: crossed forearms over the baggy shirt. The same
      shirt overlap shows in the full-body `thinking_face`.
  - I spot-checked 2 OKs (`e2ewave_41757`, `rt_4stood`): both agree.
- **Tests**: felt-animation 404 → **415 passed**. The new
  `tests/test_layers.py` covers the report, the unreported → full default,
  finished with layer/interrupted, wave during walk, full-body waits for
  the walk, full-body waits for a gesture, upper tags queueing, mixed
  sequences, thinking during a walk, the no-report fallback, and sitting
  upper-body posture.
- **Commits**:
  - felt-character-assets `75be8dc` (main.gd) and `8779e0c` (README).
  - felt-animation `b56f541` (overlay), `5023713` (locks), `f416db3`
    (posture) and `e0ae657` (tests).

  All pushed.
- **Left running**: felt-animation (`.venv\Scripts\python.exe -m
  felt_animation`, hidden) with the overlay it launched, on the final
  code, connected (`felt-overlay reported layers for 94 tags (22 upper)`).

### Not done / unverified

- **Found, not fixed (pre-existing, outside WP-20)**:
  - `gesture/talking/sitting`'s `sitting_talking` / `_1` clips are
    44.0 / 44.9 s long, longer than felt-animation's 30 s `CLIP_TIMEOUT`.
    A sequence waiting on them times out, releases its lock at 30 s, and
    the next full-body tag then interrupts them (seen live:
    `no completion notice ... within 30.0s`, then `(interrupted)`).
    Fix by trimming the clips or raising the timeout.
  - `_stand_up_if_sitting` (presence walks) plays `transition/sit_to_stand`
    but never sends `idle`. main.gd then reverts to its last idle posture,
    `idle/sitting`, until the next idle refresh. The ambient stand-up and
    the reply path aren't affected. It was the same before WP-20.
  - Repeat-avoidance can pick the same clip twice when an idle clip plays
    in between (the history is shared across tags). Seen with
    `thinking_face`.
- **Not judged by Mario**: whether layered big-leg clips (the jump or
  byebye_happy while walking/sitting) read well with only their upper
  body, and whether `reaction/hit` should layer instead of being
  full-body.
- **Not exercised live**: runs with a gesture on top; the listening loop
  (`reaction/listening`) over a sit; a mid-fade clip switch on one layer
  (it pops at most the ≤ 50 % weight the reused slot still had, by design).

---

## WP-21

### Props system, the chest, dissolve FX, clean-house key
**Repos**: felt-character-assets (props + main.gd), felt-animation
(decisions), felt-tray (the `X` key already registered in WP-10). **Size**:
L. **Depends on**: WP-20.

**Mario's design (decided)**: Shimeji-style. She spawns stuff from time to
time. For small items, she walks to **her chest**, rummages and comes out
holding the item. Big items she conjures with a **natural-looking FX, never a
plain pop**. Clutter accumulates; **`Ctrl+Alt+X` "clean house"** dissolves
everything.

**Do**:
- **Assets** (pre-approved downloads; keep `CREDITS.md`):
  - **Kenney Furniture Kit** (CC0, low-poly; suits toon shading),
    **Poly Haven** models (CC0), **Quaternius** stylised packs (CC0),
    **Sketchfab** CC0/CC-BY (anime-style fancy chair, mug, headphones; credit
    CC-BY).
  - **Booth** anime props need Mario's pixiv login, so list any wanted ones
    for him.
  - Catalogue v1: chest, fancy chair, beanbag, mug, book, phone,
    headphones, umbrella, sunglasses, blanket, pillow, desk lamp, potted
    plant, game controller, snack bag.
- **Look**: apply MToon (or a matching toon shader) to every prop, lit by the
  same 3-light rig, so props don't look pasted in.
- **Two kinds**:
  - **Held**: a `BoneAttachment3D` on `rightHand` / `leftHand` / `head`, with
    per-prop grip offsets (tune visually; store in `props.json`).
  - **Placed**: a world-positioned node on the floor, a ledge (WP-23) or next
    to her; simple rigid-body physics on floors so a kicked mug rolls.
- **Clip → prop manifest** (`props.json` in felt-animation):
  `idle/sitting` and `sit/*` → chair (the seat height matched once to the sit
  clip's hip height, ~45 cm, so she sits *on* it), `drink_water` → mug (right
  hand), `check_phone` → phone, `listening_to_music` → headphones (head; also
  on `music_*` events from WP-16), plus weather (umbrella when it rains,
  sunglasses when it's sunny; needs a desktop hook to felt-core's weather
  cache), time of day (morning mug, late-night blanket/pillow, evening lamp),
  and game-start controller (WP-17).
- **The chest**: a permanent placed prop. Its home is the **side screen's
  floor**, which needs WP-22/23. Until then, put it at the right end of the
  primary screen's floor and make its position configurable. The lid opens
  with a simple hinge tween (no clip).
- **Fetch sequence**: walk to the chest → `crouch/enter` → lid opens →
  `prop/pickup_right` → the item attaches to her hand → `crouch/exit` → walk to
  the use spot.
- **Conjure sequence** (big items, or when far from the chest):
  `ambient/look_around` → a reach gesture → a **dissolve-in**: a spatial shader
  with a noise-threshold reveal and a glowing edge sweeping the object over
  ~0.8 s, plus a small `CPUParticles3D` sparkle/dust puff (CPU particles are
  safe on the Compatibility renderer). Disappearing is the same in reverse.
- **Clutter rules** (felt-animation):
  - max ~6 placed items;
  - never place over the focused window's centre (a weight, not a rule, since
    Mario is fine with some overlap);
  - items older than a few hours are candidates for her tidying up (walk
    over, pick up, carry back or `prop/throw_*` into the chest);
  - when annoyed, she sometimes `prop/kick`s a dropped item.
- **Clean house** (`Ctrl+Alt+X` → felt-animation `POST /props/clear`): every
  placed/held prop except the chest dissolves out at once. (A broom-sweep
  version is a later nicety.)
- **Persistence**: placed items and positions saved to
  `%APPDATA%\Felt\props.json`, restored on start.
- **Relay messages** (document them in the assets README):
  - `{"prop": {"id", "action": "spawn"|"despawn"|"attach"|"detach"|"place", "bone", "pos", "fx": "dissolve"|"none"}}`
  - `{"chest": "open"|"close"}`

**Accept**:
- she sits on a real chair;
- sips from a real mug;
- fetches something from the chest without anything popping;
- conjures a big item with the dissolve FX;
- clutter persists across restarts;
- `Ctrl+Alt+X` clears it all.

### Notes from implementation (2026-09-26)

**Assets** (`felt-godot-overlay/props/models/`, credits in
`props/CREDITS.md`, 16 GLBs, 46–1239 tris each). All CC0 except three
CC-BY 3.0 items, which are credited:
- Kenney (CC0): chest (Pirate Kit), fancy chair = `loungeChair` armchair,
  pillow, desk lamp, potted plant (Furniture Kit), mug, snack bag (Food
  Kit), blanket = bedroll (Survival Kit).
- poly.pizza CC0: phone, open book, water bottle (Quaternius); headphones,
  closed umbrella (CreativeTrio).
- poly.pizza CC-BY 3.0: sunglasses (jeremy), controller (Ginsta), beanbag
  (J-Toastie).
- The water bottle is a 16th item: Mario said `drink_water` is "opening a
  water bottle and taking a sip", so that clip gets the bottle. The mug sip
  plays only that clip's sipping segment (8.0–15.2 s, left hand).
- The files are already glTF binaries. Kenney's external `colormap.png` is
  embedded by `props/embed_glb_textures.py`, with no geometry change.
  Nothing needed Booth, so there's no shortlist.
- **Look**: `props/felt_prop.gdshader` uses MToon's directional-light maths
  with her values (ShadeToony 0.7, ShadeShift -0.1, a tight rim) under the
  same 3-light rig, plus the dissolve. The MToon shader itself can't
  discard per pixel for the dissolve.

**Architecture.** felt-animation decides and main.gd only executes.
- **Manifest**: `felt-animation/props.json` is the one source. It holds:
  - the catalogue, sent as `{"prop_catalogue"}` on connect: model, size,
    rotate, stretch, grip per bone, physics, lid;
  - clip → prop, events → props, and the step sequences (tag + a timed cue,
    chest open/close);
  - the chair's sit clips and `hand_dx` (where she stands for each action).
- **Held**: a `BoneAttachment3D` per bone plus an `unscale` child. Grips are
  authored in the rest frame: -x = toward the fingertips, -y = palm side,
  +z = front. A missing left-hand grip mirrors the right.
- **Placed**: `RigidBody3D` on a floor (y = 0) with walls at the frame edges.
  - Frozen at rest.
  - After a kick or drop it simulates in the z = 0 plane (axis-locked), then
    reports `{"prop_moved"}`.
  - The visual depth sits on a `depth` child.
- **Three physics bugs found and fixed live**:
  - axis locks on a frozen body clamp the node's own transform (held grips
    came out rotated, z zeroed);
  - a frozen kinematic body's state sync drags a moving or tweened node
    (0.35 m behind the hand mid-pickup, the mug put down on its side). Bodies
    now leave the physics world while held or tweened;
  - a CollisionShape3D under a plain child node never registers (a kicked
    book fell to y = -1944).
- **Sequences** (`props.py` PropDirector). The base lock is held for the
  whole sequence; the upper lock only around full-body clips, base before
  upper.
  - `obtain` order: already held → one on the floor (walk, `prop/pickup_*`,
    attach at 0.8 s) → near the chest (fetch) → big or far (> 3 m): conjure.
  - **Fetch**: walk to the chest → lid open → `prop/pickup_right` (the hand
    reaches into the chest; the item spawns there at 0.8 s with a 0.3 s
    dissolve) → lid closed. I skipped `crouch/enter`: it ends crouched with
    the hand at her side (0.40 m, not in the chest), and `prop/chest_open`
    lifts a lid at 0.73 m. Both were measured with `probe_bones`.
  - **Conjure**: `ambient/look_around` (`lookaround_face`) →
    `gesture/pointing` → dissolve-in (0.8 s + puff) at 0.7 s. Big items are
    placed beside her, not behind her.
  - **Put down**: at a spot picked by the clutter rules, `prop/pickup_right`
    → place.
  - **Tidy**: `prop/pickup_left` → either `prop/throw_left` into the chest
    from 1.4 m (`ThrowAway_LH` tosses toward world -x, the chest's side), or
    carry it back and stash it.
  - **Kick**: `prop/kick` (right foot) with the push at 0.8 s.
- **Clutter rules** (tested):
  - cap 6: over it, the oldest become tidy candidates, and the ambient loop
    weights tidy at 40;
  - items older than 3 h are candidates (weight 8);
  - spots near her (≤ 1.6 m) and spaced out, with the focused window's
    centre ×0.2 (a weight);
  - annoyance ≥ 0.45 adds kick (10).
- **Persistence**: `%APPDATA%\Felt\props.json` holds the placed items.
  Restored on every overlay (re)connect: catalogue → chest → clutter, with
  fx none.
- **Clip mapping (spec name → real tag)**:
  - `drink_water` → `ambient` clip `drink_water` (water bottle; the mug uses
    its sip segment);
  - `check_phone` → `ambient` clip `check_phone` (phone);
  - `listening_to_music` → `reaction/listening` (headphones, conjured onto
    her head);
  - `ambient/snack` → snack bag (left hand);
  - `ambient/phone_call` → phone.
- **Events**:
  - `music_start` → headphones on; `music_stop` → off and down;
  - `game_start` → controller;
  - `weather:rain` → umbrella; `weather:sun` → sunglasses;
  - `time:morning` → mug sip; `time:evening` → lamp;
    `time:late_night` → blanket + pillow;
  - the reaction table's `prop` field → `reaction:<item>` (the book).
- **The chair** (reusable for WP-23's ledge sit). Only the UAL set shares
  one hip height. Hips joint and z are relative to her pivot:

  | Clip | Hips joint (m) | Hips z (m) |
  |---|---|---|
  | `ual1_sitting_enter` (end) | 0.51 | +0.25 |
  | `ual1_sitting_idle_loop` | 0.515 | +0.247 |
  | `ual1_sitting_exit` (start) | 0.51 | +0.25 |
  | `idle_sit_1` | 0.575 | -0.035 |
  | `idle_sit_3` | 0.607 | -0.034 |
  | `idle_sit_2` | 0.639 | +0.22 |
  | `idle_sit` | 0.66 | +0.01 |
  | `sit/chair_*` (start/loop/end) | 0.574 | +0.417 |
  | `female_act_sit_on_chair` (end) | 0.46 | +0.34 |

  - The sit uses only the UAL clips, sent with the new `clip` field.
  - Seat top = 0.425 m, 9 cm under the hip joint: Kenney seat level
    0.23/0.46 × size 0.85.
  - The chair sits at z +0.26, depth ×0.5, so the seat front stays behind
    her calves.
  - Any walk while seated stands her up first.
- **Clean house**: felt-tray's key (Mario's `ctrl+shift+X`, unchanged) →
  `POST /props/clear` → every placed and held prop except the chest gets
  `despawn fx=dissolve` at once. If she was on the chair, she stands up.
- **felt-core**: new `GET /v1/weather/now`, which returns
  `{condition: rain|sun|snow|storm|null, animation_tag, age_s}` from the
  WP-06 precompute. It was committed but **not deployed** (see below).
- **Relay (additive, documented in felt-character-assets/README.md)**:
  - `prop` actions from the spec: spawn / despawn / attach / detach / place;
  - additional `prop` actions and fields: `push`, `throw`, `instant`, `yaw`,
    `fx_s`, `puff`;
  - `chest`, `prop_catalogue`;
  - `tag` + `clip` / `start`;
  - debug: `props_probe`, `debug_view_yaw`, and `pos` in `probe_bones`;
  - out: `prop_moved`.

### Proof

Crops are in `E:\Felt\scratch\wp21\shots\`; the review set is in
`E:\Felt\scratch\wp21\review\` (10 files). Drivers: `e2e.py` (posts
`/props/debug` as text/plain, like the test page, while bursting),
`strip.py` and `revealseq.py`.
- **Build**: `Godot_console.exe --headless --export-release "Windows
  Desktop" build/windows/FeltOverlay.exe` → exit 0, pck 378,113,584 B, no
  ERROR lines (`scratch\wp21\export10.log`). Overlay log:
  `WP-21 props: catalogue of 16 items`.
- **Sits on a real chair** (`sitB_strip.png`, `seatB.png`):
  - the chair dissolves in behind her, then `ual1_sitting_enter` →
    `ual1_sitting_idle_loop`;
  - probe: `clip=ual1_sitting_idle_loop Hips=(-0.003,0.515,0.247)`; chair
    `pos=(0.000,0.000,0.260) aabb=[-0.453,0.0,0.071, 0.905,0.85,0.379]`;
  - front view: thighs on the cushion, calves in front of the seat. Side
    views (`debug_view_yaw` ±90): thighs level at the seat front, feet on
    the floor.
  - Log: `props: conjured chair (chair-8) ...`, then
    `props: sitting on chair-8`.
- **Sips from a real mug** (`sip_strip.png`, `sip2_end.png`):
  - mug at her mouth in the left hand at 11.0–13.5 s, then put down upright
    on the floor;
  - second run: `props: picked up mug-9` (the floor mug is reused, not a new
    one) → sip → `put mug-9 down at x=0.83`.
- **Fetches from the chest, nothing pops** (`fetchB_take0.png` at
  0.08 s/frame, `fetchB_strip.png`):
  - lid open (3.6 s), hand in the chest (3.70–3.94 s), the book dissolving
    in with the glowing edge (4.01–4.10 s), fully there by 4.18 s, she comes
    up holding it, lid closed;
  - log: `props: fetched book (book-12) from the chest`.
- **Conjures a big item with the dissolve** (`conj_reveal.png`): potted
  plant pixel count per 0.12 s frame:
  0 → 232 → 537 → 921 → 1228 → 1257 → 1185 → 1123 (4.57–5.54 s), i.e. a
  progressive reveal over ~0.85 s with the sparkle puff. Beanbag and chair
  conjures look the same.
- **Clutter persists across restarts** (`restored_full.png`):
  - after killing felt-animation + the overlay and restarting:
    `props: sent catalogue (16 items), chest, 2 placed`;
  - the overlay probe showed `chair-8 pos=(0.000,0.000,0.260)` and
    `mug-9 pos=(0.208,0.000,-0.250)`;
  - a later restart restored 4 (book-12, chair-13, umbrella-14,
    water_bottle-15).
- **Clean-house key clears it all** (`clean_strip.png`): the real hotkey
  (synthetic ctrl+shift+X):
  - felt-tray: `15:27:19,782 clean-house key pressed` →
    `15:27:20,007 clean house: {"status":"ok","cleared":3}`;
  - felt-animation: `props: clean house - 3 prop(s) dissolved`;
  - chair, mug and beanbag dissolve out together, and the overlay probe
    then lists only `['chest']`;
  - `%APPDATA%\Felt\props.json` → `"placed": []`.
- **Walk still smooth**: hip-x burst of a 2.3 m walk (`hipx.py
  wp21_walkx`): `frames=29 net=-2.267m moving_frames=15 backward_frames=0
  speed(moving) min=0.76 max=2.30`.
- **Also exercised live**:
  - kick: `props: kicked headphones-11`, which rolled 0.69 m and settled;
  - tidy: `props: tidied headphones-11 (threw it into the chest)`;
  - held umbrella conjure; the water bottle in the full clip;
  - autonomous events: `music_start -> headphones` (twice) and, while Mario
    played PoE2, `game_start -> controller`;
  - ambient sit on a conjured chair.
- **Tests**: felt-animation 415 → **446 passed** (`tests/test_props.py`,
  31 tests: manifest vs the real library and models, clip mapping, catalogue
  fields, clutter cap/age/spot/focus weight, persistence, fetch, conjure,
  pickup reuse, use + switches + segment, sit (conjure / walk to a chair),
  stand before walking, tidy, forced tidy, kick, prop_moved, clear, props
  off, endpoints). felt-tray 142 → **143** (clean key posts `/props/clear`,
  survives felt-animation being down). felt-core 356 → **359** (weather
  endpoint).
- **Commits (all pushed)**:
  - felt-character-assets `ce1aa64` (models + credits), `057db3f`
    (props.gd, shader, main.gd), `6590a1f` (README);
  - felt-animation `349fd21`, `3feef03`, `8120de0`, `6e21a65`, `d1da885`;
  - felt-tray `46041e2`;
  - felt-core `9473cb9`.
- **Test page**: `E:\Felt\tools\review\test-props.html`.

### Not done / unverified

- **felt-core's `/v1/weather/now` is committed and pushed but not
  deployed.** The auto-mode classifier blocked the vendored-copy step into
  clockmost-infra ("Production Deploy"), so I stopped there. Until someone
  runs deploy steps 2–4, felt-animation's weather loop sees the 404 and
  turns weather props off. The umbrella/sunglasses events work from the
  test page. After deploying, restart felt-animation.
- **Gemini review didn't run**: `agy-delegate` answered
  `error: interrupted` three times (300 s, 500 s, and a one-file 150 s
  probe). I reviewed every crop in `review\` myself.
- **Side view of the seat**: the armrests hide the exact seat contact, so
  the no-float/no-sink claim rests on the numbers (hips 0.515 m joint, seat
  0.425 m) plus the front view and the thigh line in the side views.
- **Not captured on screenshots**: the throw arc into the chest (it happened
  after the burst window; the log and state confirm it). The carry-back /
  stash variant of tidy wasn't run live.
- **Umbrella**: she carries the closed umbrella by the crook. There's no
  arm-raised clip for holding an open one overhead. Mario's "hanging from
  the tip" comment matches the open-umbrella test grid, which was
  replaced; the current grip isn't judged by him.
- **Kick**: the foot swings toward the camera but the prop can only move
  along x (2.5D), so it slides/rolls sideways. The strength
  (`kick_impulse` 2.4) isn't tuned by eye.
- **Grips**: tuned from screenshots for the mug (sip), water bottle, phone,
  headphones, sunglasses, controller, book and umbrella. The snack bag
  (left hand, mirrored grip) and the pillow/blanket were only spot-checked.
  Mario hasn't judged any of them.
- **Not run live**: `time:evening`, `time:late_night`, the weather events,
  and the reaction-table book.
- **Found, not fixed (outside WP-21)**:
  - WP-10's "come here" is mirrored: world +x is screen left, but
    `geometry.cursor_fraction_to_world_x` maps the right edge to +x. The
    props code uses the correct sign.
  - `music loop iteration failed` tracebacks come from inside the existing
    `estimate_tempo_from_audio` (3 today).
- The chair's Kenney pink hasn't had an Endfield colour pass (`tint` is
  supported in the catalogue).

### Follow-ups (2026-09-26, Mario's live review)

1. **Mug sip removed.** The `sip:mug` and `time:morning` events and the
   test-page button are gone. No clip maps to the mug any more; it stays in
   the catalogue as a plain prop. Test:
   `event_props(m, "sip:mug") is None`, and no clip entry has `item == "mug"`.
2. **Water bottle: left hand, cap with the right, off the floor.**
   - **Clip check**: `drink_water` already drinks with the **left** hand. The
     probe put the left hand at her mouth at 8.5–15 s (0.19, 1.44, -0.23),
     head 1.39. At 3.5–8 s and 15.5–19.5 s the left hand holds low
     (≈ 1.06 m) with the right hand 0.2 m above it: the cap. So **no
     mirroring was needed**.
   - Only the clip's own right-hand table pickup (0–3.3 s) and put-down
     (19.8 s–) are cut: `start 3.3`, `end 19.8`.
   - She picks the bottle up off the floor with `prop/pickup_left`. With
     `from_floor`, one fades in by her feet first if none is lying around.
     Afterwards it goes back down on the floor.
   - Left-hand grip: `pos [0.06,-0.04,0]`, `rot [0,90,90]`, picked from
     three grids (`scratch\wp21\shots\bottle_grid*.png`,
     `bottle_zoom2.png`).
   - **Proof**:
     - `bottle_segment.png` (4.2 / 6.5 s cap under her right hand's
       fingers, 9.5–14 s at her mouth, 17 s recapping);
     - end-to-end `bottle_e2e.png` / `bottle_e2e_zoom.png` (2.2 s picked up
       in the left hand, 5.6 s right hand at the cap, 11.4 s at her mouth,
       16.4 s recapping, 21.6 s put down upright);
     - log: `water_bottle-33 faded in by her feet` → `picked up
       water_bottle-33` → `put water_bottle-33 down at x=-1.87`.
3. **Headphones lower**: Head grip y 0.065 → 0.04 (`headphones_y.png`
   compares 0.065 / 0.045 / 0.035 / 0.025). `headphones_final.png`: front
   and both side views (`debug_view_yaw` ±90) show the cups over her ears
   and the band resting on her hair, not floating.
4. **Sunny: no sunglasses.** The `weather:sun` event, its ambient weight and
   the weather-loop trigger are removed, and so is the test-page button.
   Rain → umbrella stays. Sunglasses stay in the catalogue; sunny becomes a
   WP-27 summer outfit.
5. **Chest at 40 %**: size 0.42 → 0.17 m (0.19 m wide), about shin height
   beside her feet (`fetchT_overview.png`). The lid hinge is unchanged and
   still opens toward the screen edge.
   - No clip reaches lower than `prop/pickup_right`'s wrist at 0.27 m (in
     front, z -0.26). `crouch/enter` and `crouch/idle` keep the hands at
     0.40 m at her sides. The `ambient/fixing` kneel reaches 0.36–0.41 m
     (probed twice).
   - So the item now **fades in inside the open chest** (placed at chest
     height 0.03, 0.3 s dissolve), then eases up into her hand as it
     reaches the chest. I kept the bend-and-reach clip (the pickup), not a
     crouch.
   - Cue re-measured from the 0.07 s burst (`fetchT_take.png`): at the old
     0.8 s cue the book faded in at 2.79–3.04 s and reached her hand at
     3.21 s, when the hand was already rising. So the fade-in moved to 0.5 s
     of the pickup and the hand closes on the item at 0.8 s, its lowest
     point (0.76–0.92 s).
   - The re-run (`fetchU_overview.png`) shows the phone inside the open
     chest at 9.13 s. It was captured at ~1 fps, because Endfield was running
     and the overlay rendered slowly, so the finer timing of that run isn't
     resolved.
   - Items wider than the small chest (the open book, 0.24 m) poke out of it
     while fading in.
- **Tests**: felt-animation **447 passed**, after `9bb5c4b`
  (446). The mug-switch test became two bottle tests (floor spawn → left
  pickup → segment → put down; a bottle already on the floor is reused).
  The manifest and fetch tests were updated.
- **Commits (pushed)**: felt-animation `a60a5f0` (no mug sip), `985f349`
  (no sunglasses), `339749c` (bottle), `707f0cc` (headphones), `bd66759`
  (chest); umbrella `fe8b7c9` (test page). No overlay rebuild was needed:
  everything is manifest/felt-animation.

---

## WP-22

### Overlay architecture for two monitors (spike + build), plus supersampling
**Repo**: felt-character-assets (main.gd + click-through patch). **Size**: L.
**Depends on**: WP-20. Discuss the result with Mario before WP-23.

**Facts**:
- DISPLAY1 is 3440×1440 at (0,0); DISPLAY2 is 1920×1080 at **(3440,357)**.
  Their bottom edges line up within 3 px (1440 vs 1437).
- The taskbar is auto-hidden (working area = full bounds).
- One transparent window **spanning both monitors crashed the AMD Vulkan
  driver** ("device lost"). That's why `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING
  := true` and the gl_compatibility renderer.

**Tension to resolve**: the review doc proposed a small **follow-window**
(the window shrinks to her and moves with her; cheap, crosses monitors freely,
makes supersampling cheap). But WP-21 **clutter** means props placed far away
from her must still render, which a window that only follows her can't do.

**Spike (≤ 1 session; write the findings into this WP)**. Try in order:
1. **One full-size overlay window per monitor** (two native windows from one
   Godot process: a second `Window` node with `embed_subwindows = false`,
   sharing the same `World3D`, each with its own Camera3D framing its
   monitor). The crash was the *single spanning* surface. Two separate
   windows may be fine. Run it for 30+ min with idle + walking + props to check
   stability.
2. If that's unstable: **follow-window for her + small native windows for each
   placed prop cluster** (same process, same world, a camera per window). Only
   a few small transparent surfaces exist at any time.
3. Either way, the click-through patch (`patch-clickthrough.ps1`) must cover
   **every** native window the process creates. Check how it finds windows
   (by PID) and extend it.

**Build** whichever is stable. Then:
- She can walk from the primary's right edge onto DISPLAY2 at floor level
  (the 3 px step is invisible). Coordinates are unified in virtual-desktop
  pixels; both monitors are at 100 % scaling. If that ever changes, the
  mapping must become per-monitor-DPI aware.
- **Supersampling**:
  - option 2 (small windows): render at 2× (`scaling_3d_scale`) for texture
    and hair shimmer; that's cheap there;
  - option 1 (full-monitor windows): test 1.5× and measure GPU load while a
    game runs. If it's too costly, keep MSAA only.
- Drop `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING` and `SMALL_TEST_WINDOW_FOR_TESTING`.

**Accept**: stable for a 2 h session including a game; she walks onto the side
screen and back; props render on both screens; clicks pass through
everywhere.

### Spike findings (2026-09-26)

**Result: option 1 works. One full-size transparent window per monitor, from
one Godot process, is stable on the AMD RX 6700 (driver 32.0.21045.5002,
OpenGL 3.3 / `gl_compatibility`).** The follow-window (option 2) wasn't
needed, so it wasn't built.

- **What ran**: the main window covers DISPLAY1 and a `Window` node
  (`embed_subwindows = false`, transparent, borderless, always on top,
  unfocusable, `mouse_passthrough`) covers DISPLAY2. Both share the root
  `World3D` (a child `Window` inherits its parent viewport's world). Each
  has its own orthographic `Camera3D`, framed through one pixel <-> world
  map. The windows are 1 px shorter than their monitors, trimmed off the
  TOP so they still touch side by side (the old 1 px trim off the width
  would leave a 1 px seam through her).
- **Stability**: 3.5 min short run, then a 32 min run (17:53–18:25, stopped
  early at Mario's request: "seems to be working"). Driver
  `scratch/wp22/stab.py` looped 93 cycles: walk primary <-> DISPLAY2, a wave
  every third cycle, a prop dissolved in near her each cycle (up to 6, then
  the oldest dissolved out), and the chest (on DISPLAY2) opened and closed.
  Mario was **playing a game** (`javaw` "Homestead", GPU at 97–99 %) from
  before the start until ~18:19.
  - `scratch/wp22/monitor.ps1` logged every 5 s: overlay and total 3D GPU
    load, plus System events from `amd*`, `Display` and `Dxg*` providers,
    TDR ids 4101/141/117, and Application Error/Hang for any process.
    Result: **0 events** (log `scratch/wp22/monitor.log`). Also 0 in the
    week before; the old Vulkan crash left no System-log trace.
  - Both windows stayed normal (never minimized or lost) at all 49
    checkpoints. No device-lost in the overlay log (`ov_short1_*.log`: only
    the pre-existing `icon.svg` warning).
  - One unexplained event before the runs: in the first manual test, the
    main window was minimized once (`iconic`) during a screenshot burst.
    It didn't recur. The click-through keeper now restores any minimized
    overlay window (no activate), so that case self-heals.
- **Performance while the game had the GPU**: the overlay dropped to
  **1–13 fps** (occasionally 52–89 when the game idled), using 0–15 % of
  the GPU itself. Without the game it ran at 110–119 fps. That starvation is
  pre-existing: WP-21 saw ~1 fps with Endfield running on the single-window
  build. The single- vs dual-window numbers are in the build notes below.
- **Click-through**: the old `patch-clickthrough.ps1` only ever patched the
  first "Engine" window it found, and it only looked at *visible* ones.
  Godot creates the minimized side window hidden (`WS_VISIBLE` unset,
  iconic), so the script never saw it. A ctypes keeper (felt-animation
  `clickthrough.py`) patches every "Engine" window of the PID, visible or
  not, and then shows it with `SW_SHOWNOACTIVATE`. A `WindowFromPoint`
  sweep (20 points per monitor, plus 2 on her body) ran at every
  checkpoint: **0 of 40 and 0 of 2 hits on an overlay window at all 49
  checkpoints**, i.e. clicks pass through everywhere, including over her.
- **Found**: bursting full stitched screenshots (two full-window readbacks
  plus a PNG encode) pins the frame rate at ~2 fps. The burst now takes a
  desktop-pixel `crop`.

### Notes from implementation (2026-09-26)

**Architecture (option 1, as spiked).**
- **main.gd**: the main window covers the primary; `_build_side_views()`
  adds one `Window` per other monitor. Each window is its monitor minus the
  top pixel. The windows share one `World3D` and each has its own ortho
  camera (`_frame_camera`, z = -6, near 1 / far 11, so the WP-18 clip-plane
  fix carries over).
- **One pixel map**, `_px_to_world` / `_world_to_px`:
  - `ppm` = primary window height / `cam.size` = 313.77 px/m;
  - world x = 0 at the primary's centre (desktop x 1720), desktop-right =
    world -x;
  - the floor (y = 0) is desktop row 1332 on both monitors, 105 px above
    DISPLAY2's bottom edge instead of 108 (the 3 px step);
  - floor span x = +5.48 (primary's left edge) .. -11.60 (DISPLAY2's right
    edge); roam = +4.16 .. -10.28;
  - `move` clamps to that roam range; the prop floor's walls sit at the
    span's ends.
- **Per-monitor-DPI caveat**: both monitors are at 100 %. Godot is
  per-monitor-DPI aware and uses physical pixels with one `ppm`. A monitor
  at another scale needs a per-view `ppm`, and felt-animation would have to
  be DPI aware to read physical cursor/window pixels. This is written in
  main.gd, geometry.py and the assets README.
- **Following her across monitors**:
  - the speech bubble's `CanvasLayer` reparents to whichever window her head
    is over;
  - gaze `cursor` maps the desktop cursor through the pixel map, so it works
    on any monitor;
  - gaze `point` fractions are of the monitor she is on;
  - a new debug gaze mode `desktop` (x/y pixels) uses the same mapping
    without moving the real cursor.
- **The overlay reports its geometry**: `{"geometry": {...}}` on connect
  (map, span, roam, window rects, PID).
- **Culling**: a window with nothing within 1.5 m of its frame for 3 s skips
  its 3D pass (`disable_3d`). In practice this rarely triggers: the chest
  lives on DISPLAY2 and Mario's clutter is on the primary.
- **Click-through**:
  - main.gd no longer spawns a PowerShell. felt-animation's
    `clickthrough.py` (ctypes) patches every "Engine" window of the
    overlay's PID every 0.5 s, whether visible or minimized. It takes the
    PID from the geometry report, or from its own `Popen` before that
    report arrives.
  - A window is shown (`SW_SHOWNOACTIVATE`: no focus steal from a game)
    only once its styles are confirmed.
  - Safety net: with no relay client for 20 s, main.gd minimizes its own
    windows.
  - `patch-clickthrough.ps1` now also patches every window, but it is only
    kept for manual runs.
- **felt-animation** (`geometry.py`):
  - `estimate_from_monitors()` (Win32 `EnumDisplayMonitors`) rebuilds
    main.gd's exact numbers until the report arrives;
  - come-here: the cursor pixel on any monitor -> world x;
  - shoo: the roam end farther from the cursor. The minimum-distance rule
    is capped at 1.5 m; otherwise, from the primary's centre she could
    only shoo TOWARD a cursor on DISPLAY2.
  - ambient wander: around the middle of her monitor, crossing to the
    other one 30 % of the time;
  - walk-off: through the nearer OUTER edge. **Deviation**: it was the
    farther edge, which is now up to a 17 m walk. Walk-on lands in the
    middle of that side's monitor.
  - props: floor spots across both screens, the focused window mapped
    from desktop pixels.
- **The chest's home is DISPLAY2's floor**: `props.json` `chest.desktop_x`
  = 5072 (85 % across DISPLAY2, world -10.68), configurable. It falls back
  to `x` and is clamped inside the floor. A fetch from the primary is now
  "far" (> 3 m), so she conjures instead, as the WP-21 rules say.
- **Supersampling decision: MSAA 2x only (`RENDER_SCALE` stays 1.0).**
  `{"render_scale": s}` is there to try it. Numbers are below. At 1.5× the
  walk dropped from 109 to 86 fps. While a game has the GPU the overlay
  already starves at 1–13 fps at 1.0×, and 1.5× means 2.25× the pixels.
  - GPU-load caveat: the busy % from the Windows counters is relative to
    the current clock. At idle clocks it hardly moves with scale, because
    the GPU clocks up.
- **Dropped**: `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING` and
  `SMALL_TEST_WINDOW_FOR_TESTING`.
- **Relay additions** (documented in the assets README):
  - out: `geometry`;
  - screenshot options: `window` (`all` = stitched desktop, `primary`,
    `screen1`) and `crop`;
  - debug: `perf`, `render_scale`, `view_culling`, `view_visible`,
    `view_vsync`, gaze `desktop`.

### Proof

Scripts and logs are in `E:\Felt\scratch\wp22\`; review crops are in
`scratch\wp22\review\`.

- **Build**: `Godot_console --headless --export-release` gave exit 0, pck
  378,120,976 B, and no errors (the only overlay stderr line is the
  pre-existing `icon.svg` one). Startup log: `WP-22 side view: screen 1
  window pos=(3440, 358) size=(1920, 1079)` and `WP-22 world span
  x=[-11.601, 5.482] roam=[-10.278, 4.158] ppm=313.766 views=2`.
- **Stability**: see the spike findings. 3.5 + 32 min, about 26 min of it
  with Mario's game at 97–99 % GPU. **0 display/driver/app-crash events**,
  both windows normal throughout, no device-lost. The run was stopped early
  at Mario's request; he watched it working. Short sessions on the final
  build since then: clean.
- **She walks onto DISPLAY2 and back** (shoo through felt-animation's own
  locks, cropped bursts, `hipx2.py`, which isolates her from floor props by
  her head column):
  - DISPLAY2 -> primary: 12.64 m, 93 frames, 79 moving, **0 backward**,
    0.38–2.51 m/s.
  - Primary -> DISPLAY2: 14.35 m, 103 frames, 91 moving, 1 backward: the
    -0.33 m/s turn-back settle 0.5 s before arrival, the same one WP-18/20
    documented. **0 backward while stepping.**
  - Across the seam: 1.27–1.46 m/s, no jump.
  - Crops (`seam_crossing.png`, `seam_crossing_back.png`): straddling the
    seam she isn't cut, doubled, shifted or resized; the feet stay on the
    same line.
- **WP-20 layers**: wave while walking across both monitors (`/presence
  move` + `/debug/play_tag gesture/wave`). Probe mid-walk:
  `base=walk_forward (locomotion/walk/normal_walk)`,
  `upper=goodbye (gesture/wave) weight 1.0`; overlay notices
  `{"finished": "gesture/wave", "layer": "upper"}` then `arrived`. 94
  frames, 0 backward, 0.51–2.48 m/s (`wave_while_walking_seam.png`).
- **WP-21 props on both screens**:
  - Fetch from the chest on DISPLAY2 (`fetch_on_display2.png`): lid open,
    reach in, book in hand, put down. Log: `fetched book (book-41) from the
    chest` -> `put book-41 down at x=-9.92`.
  - Conjure on DISPLAY2: potted plant pixels per 0.1 s
    0 → 179 → 446 → 708 → 1105 → 1279 → 1143 (a progressive ~0.5 s reveal,
    `conjure_on_display2.png`).
  - Probe: chest at -10.68 plus the book and plant on DISPLAY2; Mario's
    clutter (controller, lamp, headphones, phone, snack bag, bottle) on the
    primary.
- **Gaze on both monitors** (`gaze_primary.png`, `gaze_d2.png`, the debug
  `desktop` mode = the cursor mapping):
  - with her on the primary (desktop x 2347), targets at x 200/1300 turn
    her head screen-left and targets at 3440/4400/5300 (the seam and
    DISPLAY2) turn it right;
  - on DISPLAY2 (x 4387), targets on the primary and at the seam turn it
    left, and 5300 turns it right; camera mode faces front.
- **No slicing**: `recover/getup_back` and `climb/2m` on DISPLAY2
  (`getup_on_display2.png`, `climb_on_display2.png`): whole body in every
  frame.
- **Clicks pass through everywhere**, on the final build as launched by
  felt-animation: `WindowFromPoint` found **0/192** grid points (12×8 per
  monitor), 0/10 on her body and 0/7 on props hitting an overlay window.
  After stripping `WS_EX_TRANSPARENT` by hand, the keeper re-applied it in
  0.23 s.
- **Supersampling / cost** (`perfab_idle2.txt`, no game running, 20 s per
  config; fps = overlay median; GPU = the overlay's 3D busy %, at whatever
  clock the GPU chose):

  | config | fps | GPU busy |
  |---|---|---|
  | two windows, 1.0× (as built) | 110 | 63.7 % |
  | DISPLAY2 window hidden (= the old single window) | 128 | 63.1 % |
  | two windows, DISPLAY2 vsync off | 120 | 68.0 % |
  | 1.5× | 100 | 65.8 % |
  | 2.0× | 95 | 67.1 % |
  | walking, 1.0× | 109 | 62.7 % |
  | walking, 1.5× | 86 | 70.9 % |

  - The overlay is CPU-bound at ~11–13 ms `process` per frame.
  - The second window costs ~15 % fps (128 → 110).
  - With a game running: 1–13 fps at 1.0×, 0–15 % GPU share (the spike's
    run).
- **Gemini review**: `agy-delegate` answered `error: interrupted` again.
  I reviewed every crop myself; all OK.
- **Tests**: felt-animation 449 → **470 passed**:
  - `test_geometry` (+6): the report vs the monitor estimate, seam
    continuity, come-here on both monitors, focused-window mapping, the
    legacy fallback;
  - `test_clickthrough` (5);
  - `test_props` (+4): chest from `desktop_x`, fetch on DISPLAY2, a
    two-monitor `pick_spot`, a focused window on DISPLAY2;
  - `test_presence_endpoint` (+3, 4 updated);
  - `test_multimonitor_server` (3).
- **Commits (pushed)**:
  - felt-character-assets `ddb4893` (main.gd, props.gd, ps1) and
    `0b8562b` (README);
  - felt-animation `4dec410` (geometry), `77147c8` (click-through),
    `17f008c` (presence/props/server/chest) and `b1f1f44` (README);
  - umbrella `9c5a28c` (spike findings).
- **Left running**: felt-tray, felt-animation (hidden, it launched the
  overlay) and one FeltOverlay (pid 6304, both windows patched, 111 fps).

### Not done / unverified

- **The 2 h session with a game is Mario's to confirm in normal use.** I
  ran 3.5 + 32 min (26 min of it with his game) with 0 driver events. Mario
  saw it working and asked to skip the rest.
- **While a game has the GPU she runs at 1–13 fps**. That's no worse in kind
  than WP-21's ~1 fps on the single window. It wasn't A/B'd under a game
  (the game had ended), so the second window's share of the slowdown under
  load isn't measured. Possible levers if it matters: vsync off on the
  side window (+10 fps idle, untested for stability, so not enabled), a
  frame cap, or skipping the DISPLAY2 3D pass more aggressively.
- **GPU cost at a fixed clock** isn't measurable here: LibreHardwareMonitor
  isn't running elevated (no power/clock sensors), and the Windows busy %
  and Godot's GPU timer both move with the clock.
- **One unexplained minimize** of the main window during the first spike
  test (it didn't recur). The keeper now restores minimized windows, so
  Show Desktop (Win+D) no longer hides her for good. That behaviour is a
  change: tell Mario if he wants Win+D to hide her.
- **Culling** rarely triggers with the chest permanently on DISPLAY2. The
  "window 3D off" -> on switch while she crosses wasn't separately
  measured for a hitch; the crossing bursts show none.
- **The real cursor was not moved** (Mario was using the PC). Gaze uses the
  same mapping through the `desktop` debug mode, and one real-cursor
  sample was taken, but not a cursor sweep.
- `Update Felt.bat` / `UpdateFelt.ps1` still copies `patch-clickthrough.ps1`
  next to the exe. That's harmless (nothing runs it), and I didn't touch
  it per the rules.
- Not touched: WP-23 surfaces (the DISPLAY2 grid seam at y≈897 maps
  through `_px_to_world`: world y = 1.949 - (897 - 720.5) / 313.77 =
  1.39 m; ledges come from desktop pixels the same way).

---

## WP-23

### Desktop world: platforms, ledges, falls, riding windows
**Repos**: felt-animation (world model + decisions), main.gd (movement and
physics execution). **Size**: L. **Depends on**: WP-22, WP-21.

**Mario's decisions**:
- size stays 100 % (~540 px tall);
- both monitors;
- she **may overlap windows** ("it's fine she covers a bit … also why we have
  the shoo keybind"), with no automatic fleeing (`Ctrl+Alt+M` is the shoo);
- surfaces v1 are the floors of both screens, visible window top edges, and
  the side screen's 2×2 grid seam (Mario keeps DISPLAY2 split into 4; the
  bottom quadrants' top edges sit at y ≈ 897, exactly 540 px below that
  screen's top);
- roaming is mood-driven, with a relocation every ~3–8 min by default
  (tray-tunable);
- window events always get a non-verbal reaction, and speech goes through
  the budget.

**Do**:
- **World model** (felt-animation, ~4 Hz): enumerate windows in z-order (the
  same approach as WP-07; consider moving the enumerator into felt-animation
  and letting felt-tray fetch `GET /windows` rather than duplicating it).
  - For each window top edge, compute the **visible segments**: subtract the
    rects of windows above it in z-order.
  - Add monitor floors.
  - **Clearance rule**: a ledge qualifies if there's ≥ her height (sitting:
    ~60 % of it) above it *within the monitor*. Overlapping other windows is
    allowed.
  - Emit `{"platforms": [{id, hwnd, x0, x1, y}]}` to the overlay when it
    changes.
- **Movement vocabulary** (the WP-18 clips):
  - walk along a platform;
  - **hop down**: `air/jump_start` → `air/fall` (gravity in main.gd) →
    `air/land_soft` or `air/land_hard` (hard above ~300 px), and after a
    very hard landing, `recover/getup_*`;
  - **climb up** small steps: `climb/1m` (≈ 340 px at her scale), `climb/2m`
    (≈ 680 px). Measure her world height → pixels once and derive these.
  - Anything bigger means going around (walk to where platforms meet) or a
    jump arc.
  - **Ledge sit**: sit on a window top edge with legs dangling. **Decided
    (Mario, 2026-09-26): use the existing sit animations**, no dedicated
    ledge clip. Play `sit/chair_start` → `sit/chair_loop` / `idle/sitting` →
    `sit/chair_end`, with her hips placed on the ledge y, so her legs hang
    over the edge in front. Match the seat height to the clip's hip height,
    the same measurement WP-21 needs for the chair.
- **Events**:
  - a window moves → she rides it (her platform offset stays constant);
  - it's minimised/closed → fall → land → annoyed face → a budgeted "rude!"
    line;
  - it's maximised → her platform vanishes → fall to the floor;
  - fullscreen app → retreat to a screen corner of the *other* monitor.
- **Choosing where to go** (felt-animation): candidates weighted by mood
  (bored → explore, sleepy → sit on a ledge or the chair), a slight
  preference against the focused window's centre, near the cursor sometimes
  (curious), and the chest when a prop is needed.
- main.gd owns only execution: a kinematic body with x/y, gravity while
  airborne, and snapping feet to the platform y. It reports `arrived`,
  `fell`, `landed(height_px)`.

**Accept**: over a normal session she:
- walks on both floors;
- hops onto and off the side-screen grid seam;
- sits on a window edge;
- rides a dragged window;
- falls and complains when her window closes;
- never ends up floating or stuck (add a watchdog: if she's not on any
  platform for > 2 s, drop her to the nearest floor).

Mario judges the feel.

### WP-23 build notes (2026-09-27)

**Starting state (explorer map):**
- Movement is **x-only**. `main.gd` clamps her feet to one global
  `FLOOR_Y = 0` every frame (`_clamp_feet_to_floor`, ~L1731). There is no
  gravity, jump or fall code anywhere.
- One borderless always-on-top window **per monitor** covers the whole
  screen (minus 1 px), all sharing one 3D world. Pixels map to world
  linearly and identically on every monitor: `_px_to_world` / `_world_to_px`,
  `_ppm`, `_origin_px`, `_cam_center_y`, reported to felt-animation in
  `{"geometry": …}`.
- Window enumeration exists only in felt-tray `capture_win32.py`
  (`enumerate_windows`, for screenshots). It has DPI-aware DWM frame bounds
  and skips cloaked, minimised and tool windows, but it **drops the z-order**.
- The clips `air/{jump_start,fall,land_soft,land_hard}`, `climb/{1m,2m,vault}`,
  `sit/chair_*` and `recover/getup_*` are on disk. Nothing plays them.

**Slices, each shippable and each judged live by Mario:**
1. **World model (felt-animation, pure Python + a Win32 adapter).**
   - `world.py`: z-ordered windows → visible top-edge segments (subtract the
     windows above) + per-monitor floors + the clearance rule →
     `platforms[{id, hwnd, x0, x1, y}]` in desktop px, then world units via
     the overlay geometry.
   - A 4 Hz loop and `GET /world` for debugging. Fully unit-tested on
     synthetic layouts (including the DISPLAY2 2×2 seam at y≈897).
   - No movement change yet.
2. **Vertical support in main.gd.**
   - `FLOOR_Y` becomes a per-body `support_y`, set by
     `{"support": {"y": …}}`.
   - When the support drops away: gravity fall → `air/fall` →
     `air/land_soft`/`land_hard` (above ~300 px) → report
     `{"landed": {"height_px": …}}`.
   - Watchdog: >2 s unsupported → drop to the nearest floor.
3. **Getting around.**
   - A path over the platform graph: walk, hop down (`jump_start`→`fall`→
     `land`), climb ≤ 2 m steps (`climb/1m|2m`), otherwise route around.
   - Mood-weighted destination choice replaces the x-only ambient wander.
4. **Window events.**
   - Ride a moving window (a constant offset).
   - Minimise or close → fall + annoyed + a budgeted "rude!".
   - Maximise → fall to the floor.
   - Fullscreen → retreat to the other monitor's corner.
5. **Ledge sit.** `sit/chair_*`, with her hips on the ledge y and legs over
   the edge.

**Slice 1 ✅ (felt-animation `3ad84d4`, 2026-09-27; built by a Sonnet
agent, reviewed live):**
- **What it added:**
  - `world.py` (`compute_platforms`, pure);
  - `windows_win32.py` (z-ordered enumeration, monitors with work areas);
  - `world_loop` at 4 Hz, logging only on change;
  - `GET /world`;
  - 8 synthetic-layout tests.
- **Live check on Mario's desktop:**
  - monitors: 0..3440×0..1440 (primary) and 3440..5360×357..1437 (side);
  - platforms: `floor:0` y=1440, `floor:1` y=1437, and **the 2×2 seam
    emerges by itself** from the snapped bottom-left quadrant window
    (x 3440–4400, y 897).
  - So the `extra_seams` parameter isn't needed live, and there's no
    hardcoded seam.
  - Maximised windows and top edges too near the monitor top (y 142, y 357)
    are correctly dropped.
  - The overlay's own windows don't enumerate at all (they're
    unfocusable/tool windows).
- **Still unverified:** `her_height_px` = ppm × character height from the
  overlay geometry report (540 fallback). Check `GET /world` once
  felt-animation restarts on this build.

**Slice 2 ✅ (felt-character-assets `63564e4`, felt-animation `4330a96`; Mario 2026-09-27: "fall looks amazing";
Sonnet agent, diff reviewed; the headless export compiled clean). Needs
Mario's feel check:**
- **What it does in `main.gd`:**
  - `FLOOR_Y` became `_support_y`.
  - `{"support":{"y_px"}}`: below her feet → a gravity fall (9.8 m/s²,
    12 m/s terminal) with `air/fall` re-triggered while falling, then
    `air/land_hard` (drop > 300 px) or `land_soft`, and she broadcasts
    `{"landed":{"height_px"}}`. Above her feet → an instant snap
    (climbing is slice 3).
  - `{"lift":{"height_px"}}` is the test hook.
  - Watchdog: falling for > 2 s, or more than 2× her height below the fall
    start → snap to support, and `landed` gets `watchdog: true`.
  - A `move` that arrives mid-fall is queued (last one wins).
- **felt-animation:** `POST /debug/drop` and `POST /debug/support`, plus
  logging of `landed`. 6 tests.
- **Nothing automatic yet.** Only the debug hooks move her vertically.

**Slice 3 ✅ (Mario 2026-09-27 "looks fine"; + sync fix `2da622c` and the Ctrl+Alt+G "go to the ledge under the cursor" action, felt-animation `ddced58` / felt-tray `0f2777c`; felt-animation `2a7c6e3`, felt-character-assets
`3231e3a`, 2026-09-27; Sonnet agent):**
- **`navigation.py` (felt-animation, pure):** BFS over the platform graph -
  `Walk`/`HopDown`/`Climb` steps. Hop down: any lower platform whose
  x-range overlaps hers. Climb: only when the rise is <= ~2 m (`ppm` from
  the overlay's geometry report converts px to metres), picking the
  smallest clip (`climb/1m`/`climb/2m`) that covers it; too tall -> no
  direct edge, routed via a floor instead (every floor is mutually
  walk-connected, since WP-22's walk already spans monitors). 11 tests,
  including the DISPLAY2 seam (897 px on the side monitor, a climb/2m from
  that floor) and an unreachable/too-tall case.
- **Platform tracking (felt-animation):** `AppState.current_platform_id`/
  `pending_platform_id`. `loops._sync_platform_support` runs every world
  tick (4 Hz): anchors to the floor under her on the first tick; otherwise,
  if her platform vanished or no longer contains her x, sends
  `{"support"}` toward the highest platform below her feet (`world.
  pick_landing_platform`, else the floor) - skipped while
  `state.behavior.base_busy` (an active walk/fall/hop/climb already owns
  her). `pending_platform_id` only commits to `current_platform_id` on a
  real `{"landed"}`/`{"climbed"}` notice (`AppState._on_world_settled`).
- **main.gd:** `{"hop": {"y_px"}}` (plays `air/jump_start`, then the
  existing slice-2 fall) and `{"climb": {"y_px", "meters"}}` (plays
  `climb/1m`/`climb/2m`, lerps `character.position.y` to the new support
  over the clip's own duration - **guess:** these clips' root motion isn't
  trusted to raise her the full step, flagged for Mario to judge live).
  Both suspend feet-clamping and queue a `move` the same way a fall
  already does, and reply `{"landed"}`/`{"climbed"}` on completion.
  Documented in `felt-character-assets/README.md`.
- **`nav_executor.py` (felt-animation):** runs a plan step by step, holding
  the base lock for the whole thing (so the tick-based glue above doesn't
  race it); each `HopDown`/`Climb` step is bounded by an 8 s timeout
  (`wait_for_landed`/`wait_for_climbed`) and aborts the plan on a miss.
  **Known gap:** a `Walk` step's own timeout doesn't currently abort the
  plan the same way (`walk_body` doesn't report success/failure) - only
  logs a warning. 6 tests against fakes.
- **Ambient wander (felt-animation):** `_ambient_walk` picks a platform
  target `PLATFORM_ROAM_CHANCE` (0.35) of the time instead of a floor x -
  mood-weighted (`_platform_roam_weight`): boredom favours further/higher
  platforms, low energy ("sleepy") favours nearer/lower ones, a small
  constant pull toward the cursor stands in for "curious" (**guess:**
  mood.py has no dedicated curiosity axis - see `MOOD_KEYS`), and a slight
  penalty near the (approximated - the topmost window-kind platform, not a
  real foreground-window query) focused window's centre. Never a platform
  narrower than her width (`_her_width_px`, via `ppm` and
  `character_width`). `FELT_PLATFORM_ROAM_ENABLED` (default on) disables it
  entirely.
- **`POST /debug/goto`** `{"platform_id", "x_px": float|null}` plans and
  runs a route in the background; `GET /world` now also reports
  `current_platform_id`.
- **Verification done:** `uv run python -m pytest -q` (534 passed), `ruff
  check`/`format --check` clean, `ty check` clean, `check_env_example.py`
  OK, headless Godot export compiled clean (gdlint's pre-existing main.gd
  findings are unrelated baseline noise per ENGINEERING-RULES.md's
  report-only convention, not something this slice touched).
- **Not done / unverified:** nothing live-checked on Mario's real desktop
  yet (no running felt-animation/overlay in this session) - the climb
  root-motion guess, the platform-roam mood weights, and the DISPLAY2 seam
  hop/climb specifically need his live judgement. Ledge sit (slice 5) and
  window events (slice 4) are still open.

**Slice 4 🔎 needs review (felt-animation, felt-character-assets; 2026-09-27;
Sonnet agent, no live session running - see "Not done" below):**

- **New module `window_events.py`** (felt-animation), kept separate from
  loops.py per the WP's own instruction. Pure functions (unit tested on
  synthetic data, same style as world.py/navigation.py) plus thin async
  orchestrators loops.py's world tick calls:
  - `detect_ride`/`try_ride`: compares the SAME hwnd's raw rect between
    this tick and the previous one (needed a new `AppState.world_windows`
    cache of the raw, unsegmented window list - the occlusion-clipped
    `Platform` segments alone can't answer "did the window itself move").
    A move within her platform's x-range after applying the same dx ->
    `{"shift": {"dx_px", "y_px"}}` (new main.gd message, instant - no walk,
    no fall/land clip); off the end -> falls through to the ordinary
    vanish/fall sync unchanged. Runs before `_sync_platform_support` each
    tick and skips it outright on a successful ride (a ride is not a fall).
  - `classify_fall_cause`: reused `world.covers_whole_monitor`/
    `world.monitor_for_point` (made public this slice - they were the
    right check already, just underscore-private; renamed rather than
    duplicated, per ENGINEERING-RULES §1.3/§1.5) to tell "vanished" (hwnd
    gone - closed or minimised, indistinguishable and both fine per the
    WP), "maximised" (hwnd still there, now covering its monitor's work
    area) and "moved_away" (hwnd still there, elsewhere/occluded) apart.
    `loops._sync_platform_support` now takes the tick's raw `windows`/
    `monitors` (both default to `()` - every pre-slice-4 test call site
    keeps working unchanged) and records the cause on
    `AppState.pending_fall_cause` right when it sends the real `{"support"}`
    that will make her fall - never for a deliberate nav_executor
    hop/climb, which never calls this function.
  - `react_to_landing`, fired from `AppState._on_world_settled` on a real
    `{"landed"}` whose fall carried a cause: **non-verbal always** -
    `emotion/annoyed` (vanished/moved_away) or `emotion/surprised`
    (maximised) via the existing `behavior.run_sequence`/
    `library.resolve_known_tag` path (both tags already exist in the
    library, confirmed on disk: `emotion/annoyed`, `emotion/surprised`).
    **Speech only through the budget**: Mario's brief said to reuse
    whatever `play_presence_line` does rather than a fresh felt-core round
    trip for a canned line - so this is a small local pool
    (`WINDOW_ANNOYED_LINES = ("rude", "standing_there", "wow_okay")`,
    sounds.json's `presence/<line>_*.wav` convention, same graceful
    "uncurated -> silently nothing" degrade every other presence line
    already has), rotated with no immediate repeat
    (`pick_annoyed_line`), a 45s cooldown
    (`WINDOW_EVENT_SPEECH_COOLDOWN_S`) so a burst of the same cause can't
    become a burst of lines, and gated by the new
    `FELT_WINDOW_EVENT_SPEECH_ENABLED` config/`.env.example` setting
    (item 5's "config constant to disable window-event speech"). A
    maximise never speaks (a judgement call: "surprised", not "rude" -
    not Mario's own wording, flagged here).
  - `maybe_retreat_from_fullscreen`: the foreground window (new
    `windows_win32.foreground_window_rect`, deliberately NOT filtered
    through `enumerate_windows_z_order`'s title/tool-window rules, since
    some exclusive-fullscreen games/players report an empty title that
    enumeration would otherwise skip) covering her own monitor's FULL
    bounds (`monitor.bottom`, taskbar included - not the work-area check
    `covers_whole_monitor` uses for maximised) -> `plan_route` +
    `nav_executor.run_plan` (background task) to a corner of the OTHER
    monitor's floor. `AppState.fullscreen_retreat_active` latches so it
    plans once per episode, not every 4 Hz tick, and clears the moment
    the foreground window there is no longer fullscreen. No-op with one
    monitor (`len(monitors) < 2`).
  - **New `AppState` fields**: `world_windows`, `pending_fall_cause`,
    `fullscreen_retreat_active`, `window_event_last_line`,
    `window_event_last_spoken_at`.
  - **main.gd**: `_handle_shift` (new, next to `_handle_support`/
    `_handle_hop`) - `_character_pivot.position.x -= dx_px / _ppm` (same
    sign convention as `_px_to_world`'s x) plus the same "snap `_support_y`
    and clamp feet" logic `_handle_support`'s upward case already used,
    skipped outright while `_falling`/`_hopping`/`_climbing`. Documented in
    `felt-character-assets/README.md`'s relay table.
- **Tests**: `tests/test_window_events.py`, 28 new (pure ride/cause/
  fullscreen/retreat-target/annoyed-line logic, plus the async
  orchestrators against fakes, following test_platform_tracking.py/
  test_nav_executor.py's patterns) - `uv run python -m pytest -q`: 567
  passed total (539 before this file existed, +28 new, 0 regressions).
  `test_platform_tracking.py`'s shared
  `_setup` helper needed one addition (`pending_fall_cause` reset) - the
  new field is a real singleton (`runtime.state`) attribute that
  `_sync_platform_support` now always sets on a real fall, and that
  file's own tests call it directly without going through the full
  `_on_world_settled`/task machinery, so an unreset stale value from one
  test crashed a later synchronous test's `asyncio.create_task` (no
  running loop) - found by running the full suite, not just the new
  file, fixed the same way `pending_platform_id` was already isolated
  there.
- **Verification done**: `uv run python -m pytest -q` (567 passed),
  `ruff check`/`format --check` clean, `ty check` clean,
  `scripts/check_env_example.py` OK, headless Godot export
  (`Godot_console.exe --headless --export-release "Windows Desktop"`)
  exit=0, no script errors in the export log (only the known, harmless,
  pre-existing "Failed to find required VRM keys" v0-preflight prints -
  see WP-18's own notes on that).
- **Guesses / judgement calls flagged for Mario**:
  - Ride detection uses the moving window's OWN rect (not the
    occlusion-clipped platform segment) for the dx/range check - occlusion
    changes introduced by the same drag aren't specifically re-validated
    on the ride tick itself; the very next tick's ordinary sync would
    catch her floating if that ever actually happens live.
  - `moved_away` (a window moved elsewhere without dragging her, or got
    occluded where she stood) gets the SAME `emotion/annoyed` + budgeted
    line treatment as `vanished` - the WP's own text only spells out
    vanished/closed explicitly; grouping moved_away with it (rather than
    inventing a fourth silent case) is this session's call, not Mario's.
  - Maximise reaction is non-verbal only (no speech at all, not merely
    lower-budget) - the WP said "speech optional/budgeted" for maximise,
    read here as "off by default" since Mario's own example lines
    ("Rude!", "Hey! I was standing there.") read as annoyance, not
    surprise.
  - The other-monitor retreat corner is a fixed near-edge margin
    (`RETREAT_CORNER_MARGIN_PX = 80px`) toward whichever OTHER monitor
    sorts first (only two monitors exist on Mario's desktop today, so
    "the other one" is unambiguous there); with 3+ monitors this always
    picks the same one rather than the nearest.
  - `standing_there`/`wow_okay` are brand-new presence-line ids with no
    curated `.wav` yet (only `rude`/`back`/`zip_it` have takes from
    WP-19) - the pool degrades to whichever of the 3 has real files, and
    is completely silent until Mario curates at least one.
- **Not done / live-unverified** (no felt-animation/overlay running this
  session, per Mario's own bounds for this task - "don't restart Felt"):
  everything above is unit-tested and export-clean only, not judged live.
  Specifically unverified: riding a real dragged window, the annoyed
  reaction/line actually firing on a real minimise/close, the surprised
  reaction on a real maximise, and the fullscreen retreat actually walking
  to the other monitor and not re-triggering while the fullscreen episode
  continues. Ledge sit (slice 5) is still open after this.
