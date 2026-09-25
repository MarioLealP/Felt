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
  - **Ledge sit**: sit on a window top edge with legs dangling. It needs a
    ledge-sit clip; source one in WP-18 Part B (Quaternius/Bandai, or
    felt-t2a-studio: "sits on a ledge swinging legs").
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
