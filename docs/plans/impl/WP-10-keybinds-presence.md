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
