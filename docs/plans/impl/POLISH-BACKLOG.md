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
- **WP-19 sounds deep dive**: see README. Covers laugh/giggle sources, a
  breath-preserving converter, and `ooh`/`mm-hm` mappings.
