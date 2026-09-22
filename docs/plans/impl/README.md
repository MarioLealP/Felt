# Felt implementation work packages

Turns the design in `../felt-review-2026-09-22.md` into implementation-ready
work packages (WPs). They're written so a fresh agent session (e.g. Sonnet)
can pick one up cold.

## How to use (for the implementing agent)

1. Read `00-implementer-context.md` fully. It has the standing rules,
   machines, deploy flow and gotchas.
2. Pick the **first unticked WP whose dependencies are done** (table below),
   unless Mario named one.
3. Read that WP file and implement **only** it. Verify it for real (each WP
   has acceptance checks).
4. Tick it here, add "Notes from implementation" at the bottom of the WP, and
   commit (component repo + this umbrella repo).

Mario reviews each WP's result live before the next one builds on it. Stop
after one.

**Delegated WPs** (Gemini via Antigravity, or OpenHands): see
[`DELEGATION.md`](DELEGATION.md) for which WPs suit which agent, the
evidence-first reporting rules, and the prompt to paste. Delegated WPs end in
`🔎 needs review` and are ticked only after verification.

## Status

| WP | Title | Depends on | Size | Status |
|---|---|---|---|---|
| **Phase 1: fix the reaction path** |||||
| [WP-01](WP-01-anim-tag-fix-logs-tests.md) | felt-animation: unknown-tag freeze fix, file logs, test suite | none | S | ☐ |
| [WP-02](WP-02-core-screen-context-rework.md) | felt-core: observations out of chat history, privacy gap, always-spoken screen reactions | none | M | ☐ |
| [WP-03](WP-03-core-quick-wins.md) | felt-core: image-skill guard, parallel router/privacy, speech-style output | WP-02 | S | ☐ |
| [WP-04](WP-04-latency-metrics.md) | Latency metrics end to end | WP-03 | M | ☐ |
| **Phase 2: the reaction pipeline** |||||
| [WP-05](WP-05-cloud-models-governor.md) | felt-core: cloud model split (Gemma 4 / Flash Lite) + quota governor | WP-04 | M | ☐ |
| [WP-06](WP-06-skill-replies-cloud.md) | felt-core: skill replies phrased in the cloud (result-gated), short spoken style, weather cache | WP-05 | M | ☐ |
| [WP-07](WP-07-screen-capture-v2.md) | Screen capture v2: per-window capture + blocklist + Gemma vision reactions | WP-05 | L | ☐ |
| [WP-08](WP-08-playback-sync-stop.md) | Playback moves to felt-animation: voice/lips/body in sync, stop | WP-01 | M | ☐ |
| [WP-09](WP-09-bubble-ducking-hush.md) | Speech bubble, call ducking, "shut up" hush | WP-08 | M | ☐ |
| [WP-10](WP-10-keybinds-presence.md) | Control keybinds + presence (hide / BRB / move / look / repeat / stop) | WP-09 | M | ☐ |
| **Phase 3: face and body** |||||
| [WP-11](WP-11-15-face-body.md#wp-11) | MSAA anti-aliasing | none | S | ☐ |
| [WP-12](WP-11-15-face-body.md#wp-12) | Face compositor + procedural face life | WP-08 | L | ☐ |
| [WP-13](WP-11-15-face-body.md#wp-13) | Listening pose + backchannel nods | WP-08 | S | ☐ |
| [WP-14](WP-11-15-face-body.md#wp-14) | Gaze: head/eyes follow cursor, look at camera | WP-12 | M | ☐ |
| [WP-15](WP-11-15-face-body.md#wp-15) | Mood × time-of-day system + reaction table + tone line | WP-07, WP-12 | L | ☐ |
| **Phase 4: context awareness** |||||
| [WP-16](WP-16-17-context.md#wp-16) | Music: beat sync, Spotify now-playing, LRCLIB lyrics | WP-15 | L | ☐ |
| [WP-17](WP-16-17-context.md#wp-17) | Signals: game start/stop, AFK, GPU heat, rage-click rate, call energy | WP-15 | M | ☐ |
| **Phase 5: assets and the desktop world** |||||
| [WP-18](WP-18-23-assets-world.md#wp-18) | Animation assets: Animset Pro triage + downloads + walking fix | WP-01 | M | ☐ |
| [WP-19](WP-18-23-assets-world.md#wp-19) | Sound batch: Orpheus non-verbals → RVC → Mario picks | none | M | ☐ |
| [WP-20](WP-18-23-assets-world.md#wp-20) | AnimationTree layering | WP-14, WP-18 | L | ☐ |
| [WP-21](WP-18-23-assets-world.md#wp-21) | Props system, chest, dissolve FX, clean-house key | WP-20 | L | ☐ |
| [WP-22](WP-18-23-assets-world.md#wp-22) | Follow-window overlay + multi-monitor + supersampling | WP-20 | L | ☐ |
| [WP-23](WP-18-23-assets-world.md#wp-23) | Desktop world: platforms, ledges, falls, riding windows | WP-22, WP-21 | L | ☐ |
| **Phase 6: life features** (Mario's picks; ★ = his priority) |||||
| [WP-25](WP-25-31-life-features.md#wp-25) | Proactive channel: server → desktop pushes | WP-09 | S–M | ☐ |
| [WP-26](WP-25-31-life-features.md#wp-26) | ★ The diary: day-to-day continuity | WP-07, WP-15, WP-25 | M | ☐ (readable, cheeky: decided) |
| [WP-27](WP-25-31-life-features.md#wp-27) | ★ Wardrobe: ties Tier A + Tier C together (outfit definitions, triggers, model swap) | WP-33, WP-21, WP-15 | L | ☐ (Tier A automated first; Tier C outfits from Mario) |
| [WP-28](WP-25-31-life-features.md#wp-28) | Screen-matched lighting + contact shadow | WP-07 | M | ☐ |
| [WP-29](WP-25-31-life-features.md#wp-29) | Path of Exile 2 companion (loot prices, wiki RAG) | WP-07, WP-06 | M | ☐ |
| [WP-30](WP-25-31-life-features.md#wp-30) | Hobbies while Mario is AFK | WP-21, WP-17, WP-26 | M | ☐ |
| [WP-31](WP-25-31-life-features.md#wp-31) | Calendar heads-up | WP-25 | S | ☐ |
| [WP-32](WP-32-33-wardrobe-automation.md#wp-32) | Wardrobe Tier A: source accessories and clothing assets online (+ Booth shortlist for Mario) | none | M | ☐ |
| [WP-33](WP-32-33-wardrobe-automation.md#wp-33) | ★ Wardrobe Tier A: a new tee every day (UV print areas, ≥ 60 tees, review gallery, daily pick) | none | M | ☐ |
| [Tier C](MARIO-vroid-outfits.md) | **Mario's** VRoid outfit checklist (pajamas, hoodie, rain, winter, Halloween by mid-Oct, …) | none | ongoing | ☐ |
| **Anytime** |||||
| [WP-24](WP-24-hygiene.md) | Repo hygiene (AnimToVrmaConverter junk, dead code, felt-vision docs) | none | S | ☐ |

Not packaged yet (later, per the review doc): sentence streaming (B-3), the
TTS engine / RVC speed-up (B-4), automatic memory (D-2), hands-free voice
(D-6), second-monitor-specific polish.

## Decisions baked into these WPs (so nobody re-asks Mario)

- Screen reactions: always spoken, plus a speech bubble. Frequency is set by
  cooldown and dedupe. Voice is ducked ~9 dB while call audio is active.
  "Shut up" → stop + a 10 min bubble-only hush.
- Capture: one window at a time, via Windows Graphics Capture. Blocklist:
  Discord, browsers, File Explorer, WhatsApp, Telegram, Phone Link,
  KeePassXC, banking. Discord's in-game overlay is off.
- Cloud: Gemma 4 26B for volume (vision, routing, public-skill phrasing),
  3.5 Flash Lite for conversation, 3.1 Flash Lite as overflow. No Live
  API.
- Personality: mood × time-of-day tone table (review doc RX-5).
- Keybinds: `Ctrl+Alt+` H hide/show, B be-right-back (5/15/30/60),
  M shoo/move, C come here, L look at this, R repeat, S stop/shut up,
  X clean house. Talking to her respawns her.
- Props: Shimeji-style. A chest on the side screen's floor, fetched or
  conjured with a dissolve FX, clutter builds up, `Ctrl+Alt+X` clears it.
- Rejected features, not to be re-proposed: OBS "clip that" auto-highlights,
  relaying Home Assistant/ntfy home alerts, Gemini Live API, pats/touch/drag,
  a phone as an offload node.
- Size fixed at 100 %. The desktop world uses both monitors (side screen
  2×2 grid seam), and she may overlap windows.
