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

**Order (Mario, 2026-09-26): follow the WP numbers.** The one exception is WP-34 (packaging), which goes last because it bundles everything.

Audit + fixes of WP-01…19: [`AUDIT-2026-09-24.md`](AUDIT-2026-09-24.md).

| WP | Title | Depends on | Size | Status |
|---|---|---|---|---|
| **Phase 1: fix the reaction path** |||||
| [WP-01](WP-01-anim-tag-fix-logs-tests.md) | felt-animation: unknown-tag freeze fix, file logs, test suite | none | S | ✅ |
| [WP-02](WP-02-core-screen-context-rework.md) | felt-core: observations out of chat history, privacy gap, always-spoken screen reactions | none | M | ✅ |
| [WP-03](WP-03-core-quick-wins.md) | felt-core: image-skill guard, parallel router/privacy, speech-style output | WP-02 | S | ✅ |
| [WP-04](WP-04-latency-metrics.md) | Latency metrics end to end | WP-03 | M | ✅ |
| **Phase 2: the reaction pipeline** |||||
| [WP-05](WP-05-cloud-models-governor.md) | felt-core: cloud model split (Gemma 4 / Flash Lite) + quota governor | WP-04 | M | ✅ |
| [WP-06](WP-06-skill-replies-cloud.md) | felt-core: skill replies phrased in the cloud (result-gated), short spoken style, weather cache | WP-05 | M | ✅ |
| [WP-07](WP-07-screen-capture-v2.md) | Screen capture v2: per-window capture + blocklist + Gemma vision reactions | WP-05 | L | ✅ (Mario live-reviewed 09-26) |
| [WP-08](WP-08-playback-sync-stop.md) | Playback moves to felt-animation: voice/lips/body in sync, stop | WP-01 | M | 🔎 needs review (fixed 09-25, see AUDIT) |
| [WP-09](WP-09-bubble-ducking-hush.md) | Speech bubble, call ducking, "shut up" hush | WP-08 | M | 🔎 needs review (fixed 09-25, see AUDIT) |
| [WP-10](WP-10-keybinds-presence.md) | Control keybinds + presence (hide / BRB / move / look / repeat / stop) | WP-09 | M | 🔎 needs review (fixed 09-25, see AUDIT) |
| **Phase 3: face and body** |||||
| [WP-11](WP-11-15-face-body.md#wp-11) | MSAA anti-aliasing | none | S | ✅ (Mario live-reviewed 09-26) |
| [WP-12](WP-11-15-face-body.md#wp-12) | Face compositor + procedural face life | WP-08 | L | ✅ (Mario live-reviewed 09-26) |
| [WP-13](WP-11-15-face-body.md#wp-13) | Listening pose + backchannel nods | WP-08 | S | 🔎 needs review (fixed 09-25, see AUDIT) |
| [WP-14](WP-11-15-face-body.md#wp-14) | Gaze: head/eyes follow cursor, look at camera | WP-12 | M | ✅ (Mario live-reviewed 09-26; leftovers in POLISH-BACKLOG.md) |
| [WP-15](WP-11-15-face-body.md#wp-15) | Mood × time-of-day system + reaction table + tone line | WP-07, WP-12 | L | ✅ (Mario live-reviewed 09-26) |
| **Phase 4: context awareness** |||||
| [WP-16](WP-16-17-context.md#wp-16) | Music: beat sync, Spotify now-playing, LRCLIB lyrics | WP-15 | L | 🔎 needs review (fixed 09-25, see AUDIT) |
| [WP-17](WP-16-17-context.md#wp-17) | Signals: game start/stop, AFK, GPU heat, rage-click rate, call energy | WP-15 | M | 🔎 needs review (fixed 09-25, see AUDIT) |
| **Phase 5: assets and the desktop world** |||||
| [WP-18](WP-18-23-assets-world.md#wp-18) | Animation assets: Animset Pro triage + downloads + walking fix | WP-01 | M | ✅ (Mario live-reviewed 09-26; leftovers in POLISH-BACKLOG.md) |
| [WP-19](WP-18-23-assets-world.md#wp-19) | Sound batch: Orpheus non-verbals → RVC → Mario picks | none | M | 🟡 WIP: accepted for now (38 keepers live, sync OK 09-26). Revisit with a deep dive on alternatives once every other WP is done |
| [WP-20](WP-18-23-assets-world.md#wp-20) | AnimationTree layering | WP-14, WP-18 | L | ✅ (Mario live-reviewed 09-26: good enough) |
| [WP-21](WP-18-23-assets-world.md#wp-21) | Props system, chest, dissolve FX, clean-house key | WP-20 | L | ✅ (Mario 09-26: done, a bit janky, polish much later; see POLISH-BACKLOG.md) |
| [WP-22](WP-18-23-assets-world.md#wp-22) | Follow-window overlay + multi-monitor + supersampling | WP-20 | L | ✅ (Mario 09-26: working; gaming fps and a 2 h session go in the performance pass, POLISH-BACKLOG.md) |
| [WP-38](WP-38-architecture-audit.md) | Architecture audit: system map (`docs/ARCHITECTURE.md`) + engineering rules + ranked, merged cleanup list (pulled forward ahead of WP-23, 09-26) | none | M | 🔎 needs review |
| [WP-39](WP-39-tooling.md) | Repo tooling: ruff/pyright/pre-commit + Gitea Actions CI (felt-core, felt-animation, felt-tray, felt-vision), gdlint report-only (felt-character-assets), felt-dashboard verified, WP-38's `.env.example`/README gap items | WP-38 | L | 🔎 needs review |
| [WP-40](WP-40-god-file-splits.md) | God-file splits: felt-animation server.py (2150 LOC) → runtime/behavior/loops/routers/app; felt-core brain.py → brain/ package (deployed); felt-tray capture split + HushState race fix + FeltAnimationClient; dashboard lint | WP-39 | L | 🔎 needs review |
| [WP-53](WP-53-cicd.md) | Push to main = deployed: CI → image to Gitea registry → bot tag bump in infra → deploy loop (health check, auto-revert) → ntfy alerts; felt-core first, then 5 server apps, Nitro5, desktop via WP-34. KISS: no k3s/ArgoCD | WP-39 | L | 🟡 phase 1 live for felt-core (09-27); vendored app/ removal + phase 2 apps left |
| [WP-54](WP-54-voice-v2.md) | Voice v2: IndexTTS-2.5 (Teto ref) → RVC -4 with moods, sentence streaming for chat replies | none | L | 🟡 built 09-29 (felt-voice `d2e1f55`, core `69abcf1`, tray `da13d0f`, anim `c6aeb4c`, dash `594d2dd`); waiting on Mario's laptop sudo + a real listen |
| [WP-55](WP-55-api-auth.md) | felt-core API auth (token) + clients over Caddy HTTPS, then close :8420 | none | S–M | ⬜ queued 10-01 (security review; LAN stopgap = server DOCKER-USER allowlist .74/.104) |
| [WP-56](WP-56-config-leftovers.md) | Config leftovers from the security pass: dead FELT_OLLAMA_URL, drive-rag's Gemini dependency, stale felt-llm comment, undeployed 30bba1ebc753 | none | S | 🟡 10-01: items 1, 3, 4 done; poe2rag network link fixed; SearXNG deployed (own `search` network, her web search works again); open: drive-rag's Gemini (decision), Wazuh triage (later, WP-43) |
| [WP-23](WP-18-23-assets-world.md#wp-23) | Desktop world: platforms, ledges, falls, riding windows | WP-22, WP-21 | L | ✅ 09-27 (all 5 slices; slice 5 "good enough" after the seated-loop fix `b9e4bba`) |
| **Phase 6: life features** (Mario's picks; ★ = his priority) |||||
| [WP-25](WP-25-31-life-features.md#wp-25) | Proactive channel: server → desktop pushes | WP-09 | S–M | ✅ 09-27 (live: claimed in 0.4 s, expired never delivered; audio pre-synth `db0b5cb`) |
| [WP-26](WP-25-31-life-features.md#wp-26) | ★ The diary: day-to-day continuity | WP-07, WP-15, WP-25 | M | ✅ 09-30: entries written for 09-27 and 09-28 on their next mornings, 5 self-memories formed (diary writer now local on felt-llm) |
| [WP-27](WP-25-31-life-features.md#wp-27) | ★ Wardrobe: ties Tier A + Tier C together (outfit definitions, triggers, model swap) | WP-33, WP-21, WP-15 | L | ✅ Tier C live 09-30 (16 VRM outfits + 10 recolour variants, date/night/daily/ambient/bikini rules; "all perfect"). Generated mix-and-match outfits **parked for polish** (see WP doc: shoe-as-base feet fix, outfit-level styling) |
| [WP-28](WP-25-31-life-features.md#wp-28) | Screen-matched lighting + contact shadow | WP-07 | M | 🔎 built 09-30 (tray `6098b45`, animation `837b64c`, overlay `8e45dc7`); needs Mario's look: bright window vs dark game, the shadow |
| [WP-29](WP-25-31-life-features.md#wp-29) | Path of Exile 2 companion (loot prices, wiki RAG) | WP-07, WP-06 | M | 🔎 built 09-30 (felt-core `685fdf8`, infra `f406355`); needs Mario's live check in PoE2 |
| [WP-30](WP-25-31-life-features.md#wp-30) | Hobbies while Mario is AFK | WP-21, WP-17, WP-26 | M | 🔎 built 10-01 (animation `754ec1d`, tray `aaebcd6` live on desktop; core `30bba1e` deployed 10-01 with `e5ddf11`); needs Mario's away check |
| [WP-31](WP-25-31-life-features.md#wp-31) | Calendar heads-up | WP-25 | S | 🔎 built 10-01 (felt-core `e5ddf11`, deployed 10-01 via CI - the tag bump works again); needs the 12-min test event check |
| [WP-32](WP-32-33-wardrobe-automation.md#wp-32) | Wardrobe Tier A: source accessories and clothing assets online (+ Booth shortlist for Mario) | none | M | ✅ 10-01: 12 accessories live with Mario's fits (felt-animation `b0ce07f`, overlay `205c4dc`); slots (hat/hair/face/neck/bag), worn by outfit + mood/ambient |
| [WP-33](WP-32-33-wardrobe-automation.md#wp-33) | ★ Wardrobe Tier A: a new tee every day (UV print areas, ≥ 60 tees, review gallery, daily pick) | none | M | 🔎 needs review |
| [WP-35](WP-35-animation-studio.md) | Animation Studio: contained window to browse/play/scrub every clip, build base+upper combos, inspect feet/root motion, mark clips keep/broken | WP-20 | M–L | 🔎 built 10-01: main.gd split 3563 → 1264 into 9 `components/` (each verified headless + TCP drives vs the original), studio = `Felt Studio.bat`; needs Mario's look |
| [WP-36](WP-36-llamacpp.md) | Local brain: llama.cpp `felt-llm` (Gemma 4 12B QAT) on the server's P104, one call with native tools; **full local, no cloud AI** (Gemini, Ollama, router and privacy classifier removed) | none | M–L | 🟡 live 09-29 (felt-core `24bd218`, infra `367c89a`/`7ff9501`); left: Nitro5 Ollama removal, first real day |
| [Tier C](MARIO-vroid-outfits.md) | **Mario's** VRoid outfit checklist (pajamas, hoodie, rain, winter, Halloween by mid-Oct, …) | none | ongoing | ☐ |
| **Phase 7: packaging (last, after everything else is ticked)** |||||
| [WP-34](WP-34-packaging.md) | One clean install per device: desktop = single tray app supervising everything (no console/PowerShell/scheduled tasks, Ollama folded in); Nitro5 = one install + model manifest; server bootstrap; `FRESH-INSTALL.md` | all WPs | XL | ☐ (first decision: Smart App Control / code signing) |
| **Anytime** |||||
| [WP-24](WP-24-hygiene.md) | Repo hygiene (AnimToVrmaConverter junk, dead code, felt-vision docs) | none | S | ✅ 09-27 |

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
