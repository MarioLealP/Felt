# Mario's live review: WP-07 … WP-18

Everything here is built, and the code is checked. What's left needs your
eyes, ears or hands. Tick a box, or write a note, as you go; one WP gets
ticked in `README.md` once all its boxes are done. Nothing is urgent. Do it
at your own pace, in normal use where possible.

## Just use her for a bit and notice

- [x] **WP-12 face:** her mouth moves with her speech. Idle faces (pout,
  grin, shocked…) keep their mouth shapes. No brow twitching.
- [ ] **WP-14 gaze:**
  - her head and eyes follow your mouse and feel natural;
  - she looks at you while talking;
  - no white-eyes at the top of the screen;
  - the head leans up more than down.
- [ ] **WP-14 eye flicks:** the small eye movements look alive, not jittery.
- [ ] **WP-13 nod:** while you talk to her (hold the voice key and speak),
  she nods sometimes and tilts her head.
- [ ] **WP-16 music:** play music with a clear beat. After about 15 s she
  bobs to it. A new track sometimes gets a remark.
- [ ] **WP-18 walking:**
  - she turns and walks with her feet planted, then faces you again;
  - she stands up before walking off if she was sitting;
  - she never slides without a walk cycle.
- [x] **WP-11 edges:** her outline looks clean on a **dark wallpaper**, with
  no light halo.
- [x] **WP-15 mood:** her tone and resting face shift over the day (morning
  vs late night).

## One-off checks (a minute each)

- [ ] **WP-10 hotkeys:** press each once. `Ctrl+Alt+`:
  - H: hide / show - works
  - B: be right back (and "back!" when she returns) - works
  - M: shoo - works
  - C: come to your cursor
  - L: look at this
  - R: repeat - works
  - S: shut up ("zip it" + a 10 min hush)
  - X: clean house (does nothing until WP-21)
- [x] **WP-10 tray:** the "Change action keybinds" submenu opens and
  rebinds.
- [x] **WP-07 privacy:** open Discord, a browser, and Felt's own chat window
  in turn. She never reacts to any of them. A game or other allowed app
  does get a spoken reaction.
- [x] **WP-09 bubble:** her speech bubble shows up next to her, and its text
  matches what she says.

## Needs a little setup

- [ ] **WP-09 call ducking calibration:**
  1. Set `FELT_CALL_CALIBRATION=1` in `E:\Felt\felt-animation\.env` and
     restart Felt.
  2. On a real Discord call, watch `%TEMP%\felt-animation.log` for the
     `call calibration: … p90=… max=…` lines. Note the numbers for a
     minute of silence and for a minute of a friend talking.
  3. Send me both, or set `FELT_CALL_PEAK_THRESHOLD` between them
     yourself.
  4. Set the flag back to 0.
- [ ] **WP-17 GPU temperature:** start LibreHardwareMonitor elevated once,
  so `gpu_temp_c` stops being null.
- [ ] **WP-17 games list:** tell me which games to recognise (the
  `games.toml` list). - Use the window title and recognize every game, no need to specify?
- [ ] **WP-18 run start/stop clips:** I'll send `locomotion/run/start` and
  `run/stop` to her while you watch. Are they facing the right way? (Two
  clips from the same batch played facing away.)

- [ ] **WP-18B styled walks and new clips:** I'll play them for you on
  request. Which walk styles read as *her*?
  - happy, tired, sad, angry, feminine, childish, proud, active, shy,
    elderly (Bandai)
  - formal, sneak, carry, zombie, jog (Quaternius)

  The keepers get wired to mood later. Slow styles slide until then,
  because walk speed is fixed at 1.3 m/s.

## Decisions

- [ ] **WP-16 taste memory:** OK for your listening profile ("likes X,
  skips Y") to go to Gemini with chat calls? Music is cloud-OK under your
  privacy line, but it's a stored profile, so yes or no. - Yes
