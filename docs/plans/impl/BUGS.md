# Bug queue (until the WP-37 board exists)

Live bugs Mario reported. Each one moves to a Gitea ticket once WP-37 is up.

## B-1: repetitive "you're crushing it" screen reactions during games (HIGH)

**Mario, 2026-09-27:** "she needs to stop saying you crushing it every 5s or
I will go insane, she always uses the exact same comment or very similar when
checking gameplay stuff".

**Evidence** (felt-tray log, 2026-09-27, Path of Exile):
- "Three in a row! You are absolutely unstoppable today, let's go!"
- "Yes! Another win! You are absolutely crushing this, Mario!"
- (Spotify) "Yes! AmaLee is absolutely killing it!"
- The felt-core 90 s cooldown **does work**: every call in between logs
  "on cooldown … no model call".

So the problem is:
1. **Repetition:** the same hype template every time.
2. **Hallucinated events:** "another win", "three in a row" in an ARPG with
   no wins.
3. **Too frequent for one long session:** a remark every 90 s for as long
   as the same game stays focused.

**Fix ideas** (felt-core `brain/screen_reactions.py` + prompt, felt-tray
watcher):
- **Anti-repeat:**
  - pass her last ~8 screen lines into the prompt as "don't repeat these";
  - a deterministic overused-phrase filter ("crushing", "killing it",
    "unstoppable", "let's go", "absolutely"…);
  - a similarity check against recent lines → one regenerate, else skip
    (deterministic, not the LLM deciding silence).
- **Ground it:** she describes what's actually visible, without assuming
  wins or streaks. Vary the register: observational, teasing, curious,
  quiet, not always cheering. Use the mood/tone line.
- **Session-aware cadence:** while the same app or game stays focused, the
  cooldown stretches: 90 s → 3 min → 6 min → 10 min cap. It resets on an
  app switch. Big moments come through WP-17 events instead (game_start and
  game_stop, AFK end).
- It stays "never truly quiet": the cadence is deterministic and the first
  reaction to an app is still prompt.
