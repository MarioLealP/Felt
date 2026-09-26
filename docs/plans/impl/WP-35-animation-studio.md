# WP-35 — Animation Studio (tooling)

Read `00-implementer-context.md` first. **Runs right after WP-20**: it
builds on WP-20's base and upper layers, which are what "combos" are.

Mario, 2026-09-26: "can we have some sort of studio so I can test all the
animations that exist and combos? In a contained environment?"

---

## WP-35

### A contained studio for every animation and combo
**Repo:** felt-character-assets (Godot). A small read-only hook in
felt-animation is optional. **Size:** M–L. **Depends on:** WP-20.

**Why:**
- Today the only way to see a clip is to send `{"tag": …}` to the live
  desktop overlay. That's transparent, click-through and tiny on a
  3440×1440 canvas, and it fights her own behaviour loop.
- Reviewing clips (WP-18B's styled walks, new downloads, broken retargets)
  and layer combos (WP-20) needs a proper bench. The walk debugging on
  2026-09-26 also needed ad-hoc `probe_bones` / burst-screenshot hacks.

**Do:**
- **A separate studio scene** (`studio.tscn`) in the same Godot project:
  - a normal opaque window (not transparent or click-through, not always
    on top);
  - a neutral background with a floor grid and scale ruler;
  - an orbit/zoom/pan camera, plus front/side/back/top presets and an
    "overlay view" preset that matches the desktop framing;
  - the same 3-light rig and MToon look as the overlay.
- **Launch** it without the editor, through the signed Godot template exe
  (Smart App Control): `FeltOverlay.exe res://studio.tscn` (verify the
  exported build honours a scene argument), plus a Desktop shortcut or bat.
  It never talks to felt-animation by default, so her live overlay and
  behaviour are untouched.
- **Share code, don't fork it.** Extract character loading, the animation
  library scan, the load-time clip fixes (cycle trim, hips-strip,
  `_symmetrise_cycle`), WP-20's layer controller, the procedural
  `FeltPoseModifier` (gaze/nod/bob/tilt) and the face compositor into
  reusable components that both `main.gd` and the studio use. The studio
  must show exactly what the overlay would. Refactor carefully: the overlay
  behaviour must stay identical (screenshot and measure before/after).
- **UI panels:**
  - **Library:** a tag tree built from the folders (with a clip count),
    search, and each clip's file name, length, loop flag, source pack and
    licence (from `CREDITS.md`).
  - **Transport:** play, pause, loop, speed (0.1–2×), frame step, a scrub
    bar, and a restart blend-time slider.
  - **Combos:** pick a **base** tag/clip and an **upper** tag/clip (WP-20
    layers), with weights and blend times. Show which layer the tag class
    routes to and flag the full-body overrides. Keep a queue or sequence
    mode (e.g. `transition/stand_to_sit` → `idle/sitting` +
    `gesture/talking`).
  - **Locomotion:** walk or run in place, or moving across the grid at the
    pivot's real speed. Show turn-out and turn-back, and the styled walks
    side by side.
  - **Procedural:** toggle gaze (follow the studio cursor, look at the
    camera, or a point), nod, beat-bob with a BPM, and the listen tilt.
  - **Face:** expression presets and regions, a lipsync test (type a line,
    or play a WAV plus its Rhubarb cues if available), and blink.
  - **Outfits:** switch among the character VRMs in `characters/` (WP-27
    groundwork). Read-only: never modify the files.
  - **Inspect:**
    - a bone overlay: foot angle against the floor, hips path trail,
      planted-foot markers — the checks that were done by hand on
      2026-09-26;
    - root-motion readout (the per-cycle hips travel);
    - a "sliding feet" warning.
  - **Review:** mark a clip keep / broken / needs-fix with a note. That
    writes `animations/library/REVIEW.json`. The same data feeds Mario's
    WP-18B style picks and later clip triage. Include one-click screenshot
    and short GIF/WebM capture into `E:\Felt\scratch\studio\`.
- **Optional, off by default:** a "send to live Felt" button that sends the
  current tag or combo to the running overlay through felt-animation's
  `POST /debug/play_tag`, so a studio pick can be checked in place.

**Accept:**
- Mario opens the studio from a shortcut and browses every tag and clip.
- He plays any clip at any speed and scrubs it.
- He combines a base and an upper clip (wave while walking, talk while
  sitting) and sees exactly what the overlay would show.
- He marks clips keep or broken into `REVIEW.json`.
- Her live overlay keeps running and isn't affected while the studio is
  open.
- The overlay's behaviour is unchanged by the shared-code refactor:
  before/after screenshots, plus the walk measured with no backward frames.
