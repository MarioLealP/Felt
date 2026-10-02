# Polish backlog

Things Mario accepted as "good enough for now", to revisit once every WP is
done: the "polish one day" pass, alongside the WP-19 sound deep dive. Each
item says what's still off and where to start.

- **Walk cycle still slightly wonky** (2026-09-26, WP-18): "still slightly
  wonky but much better, leave it be for polish one day".
  - What's in place now: `walk_forward` is looped in place, symmetrised at
    load from its flat-footed left side (`_symmetrise_cycle`, 7281cdb), and
    the pivot moves at the clip's natural 1.94 m/s. Measured: steps
    0.71–0.74 m, feet within 4° at mid-stance.
  - Known leftovers:
    - a slight lean into the stride and a rear-foot flick;
    - planted-foot slip of ~0.13 m/s;
    - walk/start and walk/stop face away;
    - run/start and run/stop are off because of root-motion lurch.
  - Directions to try:
    - a cleaner source clip (Bandai `childish_002` is clean but strongly
      styled; `active_*`/`tired_002` have one-frame joint glitches);
    - foot IK / foot locking against the floor;
    - the same in-place treatment for the start/stop clips;
    - per-style speeds once WP-18B styled walks get wired to mood.
- **Irises slightly off when looking up** (2026-09-26, WP-14): "she tracks
  fine, just slightly off on iris upwards".
  - Eye pitch is capped at 4° up / 7° down (a39a122) to stop the white-eye.
  - Things to check: whether 4° is too tight, and whether to drive the eyes
    from the VRM's own lookAt range (`lookAt.rangeMapVerticalUp`) instead
    of a hand-picked cap.
- **Props are a bit janky** (2026-09-26, WP-21): Mario, "really cool work
  tho, bit on the jank side but solid progress… mark as done but mark to be
  polished way later".
  - Known rough spots:
    - grip offsets per prop;
    - the chair's seat contact is hidden by the armrests;
    - the throw-into-chest isn't screenshotted, and the carry-back tidy
      variant hasn't been run;
    - kicked props only move sideways;
    - the umbrella is carried closed, by the crook.
- **Performance pass: benchmark everything, starting with gaming fps**
  (2026-09-26, WP-22). Mario: "mark it on the to be fixed later, we need to
  run some performance benchmarks i think in general".
  - Known: the overlay drops to **1–13 fps while a game runs** (110–119
    without), because Windows prioritises the foreground game.
  - Levers to measure:
    - render cheaper while WP-17 says a game is running (lower
      `render_scale`, MSAA off, lower fps cap);
    - vsync off on the side window (+10 fps idle, stability untested);
    - dropping the side window's render when nothing is on it.
  - Also benchmark:
    - voice latency end to end;
    - router/privacy after WP-36;
    - felt-animation CPU;
    - Nitro5 VRAM headroom;
    - the desktop's GPU cost during games.
  - Build one repeatable benchmark script so every later change can be
    compared.
- **WP-19 sounds deep dive**: see README. Covers laugh/giggle sources, a
  breath-preserving converter, and `ooh`/`mm-hm` mappings.
- **WP-30 hobby clips**: reading uses the seated idle (no real reading clip),
  napping has no lying-down clip, and doodling is left out (no sketchbook
  prop). Source clips per WP-18's list or felt-t2a-studio.
- **Seasonal tee weighting** (2026-10-01, WP-33; Mario: "keep the other on
  polish"): `wardrobe.roll_tee` picks uniformly from `tees_approved.json`, so
  the pumpkin tees can come up in June. The spec's season/holiday tag weights
  (Halloween in October, snowflakes in December) were never built. Approach:
  name-based or sidecar tags, out-of-season tees weighted to zero.
- **ComfyUI on the Nitro5 — parked** (2026-10-02, Mario: "We can park
  comfyui I don't care enough about it tbh"). `felt-comfyui` is a *user*
  service with no linger, so it dies when the last SSH session ends and her
  `generate_image` skill mostly fails. Fix when wanted: `loginctl
  enable-linger benylin` (mind VRAM contention with voice). Tee generation
  works around it (SSH tunnel + voice paused, see WP-33).
