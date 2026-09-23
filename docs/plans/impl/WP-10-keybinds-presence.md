# WP-10 — Control keybinds + presence (hide / be-right-back / move / come / look / repeat / stop)

**Repos**: `E:\Felt\felt-tray`, `E:\Felt\felt-animation`,
`E:\Felt\felt-character-assets` (main.gd), `E:\Felt\felt-core` (extend the
`felt_presence` skill, deploy). **Size**: M. **Depends on**: WP-09. WP-07's
"look at this" trigger must exist too.

## Decisions (Mario, 2026-09-22)

- Keys, all `Ctrl+Alt+<letter>`, a family next to the existing `Ctrl+Alt+V`
  (voice) / `Ctrl+Alt+T` (text):

  | Key | Action |
  |---|---|
  | **H** | hide / show |
  | **B** | be right back: 5 min; pressing again while away extends to 15 → 30 → 60 |
  | **M** | "shoo": she walks somewhere else, away from where she was and away from the cursor |
  | **C** | come here: walk under the cursor |
  | **L** | look at this: an immediate screen reaction, bypassing the cooldown |
  | **R** | repeat her last line |
  | **S** | stop / shut up: same as WP-09's hush |
  | **X** | clean house: implemented in WP-21; register the key now, but it's a no-op with a log line until props exist |

- **Talking to her while she's hidden/away respawns her**: she walks back in,
  answers, and stays.
- Mario's keyboard is a **Portuguese layout**. `AltGr` = `Ctrl+Alt` on
  Windows, so global `Ctrl+Alt` hotkeys can steal AltGr characters: `@`
  (AltGr+2), `€` (AltGr+E), `{ [ ] }` (AltGr+7/8/9/0). The letters above
  avoid those. **Verify on this machine** that none of H/B/M/C/L/R/S/X
  produce a character with AltGr on the active layout before shipping.
- Every action is also a tray-menu item and a voice/text intent (extend
  `plugins/felt_presence/` from WP-09: "go away for a bit", "give me five
  minutes", "come back", "come here", "move over", "look at this", "what did
  you say?"). She answers in character with a short line.

## Changes

### felt-tray
- Generalise `HotkeyManager` from two fixed combos to a dict of
  `action -> combo`, loaded from `.env` keys
  `FELT_HOTKEY_{HIDE,BRB,MOVE,COME,LOOK,REPEAT,STOP,CLEAN}` (defaults
  above). Rebindable from a tray submenu (reuse the existing
  `capture_next_combo` flow) and persisted with `set_hotkey`. Update
  `.env.example`.
- Each action calls felt-animation (below). LOOK triggers the WP-07 capture
  with `trigger=manual`.
- The voice/text hotkeys call `POST /presence {"action": "summon"}` first if
  felt-animation reports hidden/away (respawn).
- The tray shows a status line: `Felt: visible | hidden | away (12:34 left) |
  hush (7 min)`, from `GET /status` every 5 s.

### felt-animation: a presence state machine
- `POST /presence {"action": "hide"|"show"|"brb"|"summon"|"move"|"come", "x": optional}`.
- **States**: `visible`, `leaving`, `hidden`, `away(until)`, `arriving`.
  - **hide / brb**: a wave (if a `gesture/wave` tag exists) → walk to the
    nearest screen edge (reuse the ambient walk code; at the edge, keep
    walking until she's off-screen) → the overlay hides the character.
  - **hidden/away**: pause the ambient loop, drop unprompted reactions (tell
    felt-tray via `/status` so the WP-07 watcher stops sampling), and keep
    the overlay process alive but idle.
  - **show / summon / away expiry**: she appears just off-screen at the edge
    she left from and walks in. On `away` expiry she says a short "back!"
    line only if the initiative rules allow it (a single random pick from
    cached lines; fine to keep silent-with-wave for v1 and note it).
  - **brb pressed while away**: extend along 5 → 15 → 30 → 60 min.
- **move**: pick a target x on the current screen at least ~30 % of the
  screen width away from her current x, preferring the side away from the
  cursor (`GetCursorPos`). Walk there.
- **come**: walk to the x under the cursor (clamped to the roam limit).
- `/status` includes `presence`, `away_until`.

### main.gd
- `{"visible": false|true}` hides/shows the character node (and the bubble).
  While hidden, skip per-frame work that isn't needed (lipsync, blink,
  expressions) to keep GPU/CPU idle.
- `{"move": {"x": …}}` must accept targets **beyond** `_roam_x_limit` when
  `{"move": {"x": …, "offscreen": true}}` is set, so she can walk out of
  frame. Walking itself gets fixed properly in WP-18; for now reuse the
  current behaviour.

### felt-core
- Extend `felt_presence` intents as above. `ui_action` payloads map 1:1 to
  felt-animation `/presence` actions (plus `hush`/`unhush`/`repeat`/`look`).
  "Look at this" via voice → felt-tray triggers a manual capture. "What did
  you say?" → felt-animation `/repeat`.

## Tests
- felt-tray: hotkey config parsing/defaults and the action dispatch table.
- felt-animation: presence state machine transitions (pure, with a fake
  overlay and a fake clock), brb extension ladder, the move target picker
  (≥ 30 % away, away from the cursor), summon from hidden.

## Acceptance (live, with Mario)
1. Each key does its thing. The tray status line tracks it.
2. **B** twice → away 15 min, shown in the tray. The voice hotkey during away
   → she walks back in and answers.
3. **H** → she walks off; no screen reactions or ambient while hidden (check
   the logs); **H** again → she walks back.
4. **M** repeatedly → she relocates, never teleports.
5. The AltGr check is done and recorded in the notes.

## Notes from implementation (2026-09-23)

**Rebuild blocked mid-WP by Windows Smart App Control** (Mario's own
call): re-exporting `FeltOverlay.exe` after the main.gd changes got the
freshly-built binary blocked outright (`OSError: [WinError 4551] An
Application Control policy has blocked this file` - confirmed via
`Microsoft-Windows-CodeIntegrity/Operational` event log, ids 3118/3077:
"did not meet the Enterprise signing level requirements", i.e. an
unsigned local build, not a reputation-lookup delay like the couple of
one-off blocks earlier in the day that cleared themselves on retry - this
one didn't, and as a bespoke never-distributed binary it may never get a
crowd-sourced reputation to catch up on). Mario declined turning Smart
App Control off (it's one-way - no re-enabling without a clean Windows
reinstall) and asked instead: don't re-export during iteration, run
things directly, do the real exe build once everything else is done. So:
- **The exported `FeltOverlay.exe` on disk right now is the blocked
  WP-10 build** - there's no older cleared copy to fall back to, the
  export overwrites in place. It needs one more real export (which will
  hit Smart App Control again - expected, not a regression) once Mario's
  ready for the full live pass.
- For the rest of this WP's implementation and live testing, the Godot
  project was run directly through the vendored editor binary
  (`Godot.exe --path felt-godot-overlay`, no `--headless`) instead of the
  export - same `main.gd`, same TCP relay on 8765, felt-animation can't
  tell the difference. This is how every live check below was actually
  done.
- **Real bug this exposed and fixed along the way**: `OverlayClient.launch()`
  had no error handling around `subprocess.Popen` - the blocked-exe
  `OSError` was propagating straight through `server.py`'s FastAPI
  `lifespan` and taking the *entire app* down on startup, not just
  failing to spawn the overlay. Fixed to degrade the same way a missing
  exe already did (log and continue) - this was a pre-existing gap
  unrelated to WP-10's own scope, just one that only became visible once
  a launch actually started failing.

**Live-verified via HTTP + the directly-run Godot project** (real running
felt-animation server, real presence state machine, real walk/wave/
visible-toggle):
- `hide` → `leaving` → `hidden`, `show` → `arriving` → `visible`: full
  round trip, `GET /status`'s `presence` field tracked every transition.
- `move` and `come` both moved her and returned to `visible` afterward.
- `brb` → 5 min; a second `brb` call climbed to 15 min (`GET /status`'s
  `away_until` advanced correctly); eventually settled into `away`, then
  `show` brought her back to `visible` cleanly.
- **Real bug found and fixed live**: pressing `brb` twice in quick
  succession, before the first walk-off animation had finished, fired a
  *second* concurrent `_walk_offscreen()` task - `PresenceState.
  request_hide`/`request_brb` now return `"already_leaving"` (a state
  distinct from both `"walk_off"` and `"already_off"`) when a walk is
  already in flight, so the ladder still climbs but the walk-off
  animation itself only ever fires once. Re-verified live after the fix
  with the exact same rapid-double-press sequence - settled into `away`
  exactly once, no doubled wave/walk.

**AltGr check - done, but inconclusive for the layout that actually
matters.** Queried the *foreground window's* real keyboard layout (not
just this background process's own default, which would have been
misleading) via `GetKeyboardLayout`/`ToUnicodeEx`: none of H/B/M/C/L/R/S/X
produce a character under Ctrl+Alt on whatever layout was active at check
time. But the layout that was actually active was **English (United
Kingdom)**, language id `0x0809` - not Portuguese (`0x0816`), despite
CLAUDE.md's locale note. Either Mario's real typing layout genuinely is
EN-GB day to day (plausible - regional/date formatting and keyboard
layout are independent settings), or the foreground window at that exact
moment wasn't reflecting his usual one. Either way, **this specific check
should be re-run (or just eyeballed) while Mario is actually on his
normal Portuguese layout, if that's ever actually active**, before
fully trusting it - flagged rather than asserted as done, same as the
WP-09 bubble bug's own "circle back" treatment.

**Not done - genuinely needs Mario, no way around it:**
- Every acceptance check above requires a physical keyboard and his own
  eyes/judgment (does the key actually fire under his hands, does the
  tray status line read right to him, does she look like she's not
  teleporting). None of this is fakeable from here.
- The `look`/`repeat`/`stop`/`clean` hotkeys and all eight tray menu
  items are wired and unit-tested but not exercised through the real
  global-hotkey path (`keyboard.add_hotkey`) at all - only their
  underlying handler functions were called directly in tests and via
  direct HTTP calls in the live check above.
- The final real `FeltOverlay.exe` re-export and a full pass against it
  (not the editor-direct workaround) - deferred per Mario's own call
  above, to be done once he says the rest is ready.

Committed as five separate repo commits (felt-animation x2 - the
overlay.launch() fix split out from the presence work itself since it's
a standalone bug fix, not a WP-10 feature - felt-tray, felt-core,
felt-character-assets already committed for main.gd's visible/offscreen-
move support before the rebuild was attempted). No `[gemini-wip]`
commits needed - `git status` was clean in all four repos before this
WP's own edits began.
