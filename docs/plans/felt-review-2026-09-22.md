# Felt — full review and natural-interaction plan (2026-09-22)

Scope: every repo under `E:\Felt` plus the server-side felt-core deploy and the
Nitro5 felt-voice service. Based on reading the code directly, not on
changelogs. Items marked **unverified** are strong suspicions from the code
that still need a live check.

Working rule for this doc (Mario's standing preference): the whole plan is
written first; we then go through it **one item at a time** in conversation.
Nothing here is implemented yet.

> **Implementation**: this design has been turned into ordered,
> self-contained work packages in [`impl/`](impl/README.md) (start with
> `impl/00-implementer-context.md`). This doc stays as the *why*; the WPs are
> the *what/how*. One design change surfaced while writing them: Shimeji-style
> clutter (props left around the screen) conflicts with the "follow-window"
> overlay idea, so WP-22 starts with a stability spike comparing one overlay
> window per monitor against follow-window plus per-prop windows.

---

## 0. TL;DR — the five things that matter most

1. **Screen watching is wiping her conversation memory.** Every window switch
   saves a `[System Observation: ...]` message as a *user* turn in the same
   `dashboard` session that voice and text chat use. That session's history
   is capped at 20 messages (`db.get_history(limit=20)`). About 20 window
   switches push the real conversation out of her context completely. The
   chat window's history view also shows these entries as if Mario had typed
   them.
2. **Privacy gap on the screen path.** In `_chat_reply`, the whole recent
   window (history plus the new message) is checked before anything goes to
   Gemini. `process_screen_context` only checks the *description*, but still
   sends the last 6 history messages to Gemini. So a conversation that was
   kept local on purpose can leak to Google, carried along by a harmless
   screen description.
3. **Lips and body lag behind the voice.** felt-tray starts the audio the
   moment the reply arrives. felt-animation only sends mouth cues *after*
   Rhubarb finishes, and Godot starts the mouth timeline when the cues
   *arrive*. So the mouth runs late by the whole Rhubarb run time. The body
   reaction is later still: Rhubarb, then an LLM tag classification, then the
   current thinking loop has to finish, all one after another.
4. **Latency is the biggest thing stopping her feeling natural.** A voice turn
   is STT → router LLM → privacy LLM → reply LLM → Piper → RVC (3–8 s on CPU,
   per the voice runbook) → download → play. Every step waits for the one
   before it, and nothing streams. This hasn't been measured end to end yet.
   Instrumenting it is step one.
5. **She has no gaze and no real locomotion.** Nothing points her head or
   eyes anywhere. Walking changes only `position.x`, with an exponential lerp
   (fast start, slow crawl) and no turn of the body. So she walks in place
   facing the camera while sliding sideways, and the feet visibly skate as
   she slows down.

---

## 1. Current architecture snapshot

```
hotkey/mic ─► felt-tray ──HTTP──► felt-core (server, 192.168.1.110:8420)
                 │                    ├─ router LLM (qwen2.5:1.5b, Nitro5 Ollama)
                 │                    ├─ privacy LLM (same model)
                 │                    ├─ reply: Gemini flash-lite (cloud) or llama3.1:8b (local)
                 │                    └─ felt-voice (Nitro5): faster-whisper STT, Piper TTS (+ RVC Teto)
                 │◄── WAV + X-Reply-Text / X-Animation-Tag headers
                 ├─ plays WAV (winsound, temp file)
                 └─POST /reply_ready─► felt-animation (desktop :8421)
                                          ├─ Rhubarb lipsync (local exe)
                                          ├─ classify_reaction (desktop Ollama, qwen2.5:1.5b)
                                          ├─ state machine + ambient loop
                                          └─TCP :8765─► FeltOverlay.exe (Godot)

window switch ─► felt-tray watcher ─► felt-vision (desktop :8080, llava) ─► felt-core /v1/context/screen
```

Three different Ollama instances are in play: Nitro5 (felt-core's router, privacy
check and local chat), desktop (felt-animation's classifier and felt-vision's
llava), plus Gemini in the cloud. llava running on the desktop GPU competes
with games for VRAM.

---

## 2. Code review — findings by repo

Severity: **B** = bug (wrong behaviour today), **P** = privacy/security,
**N** = naturalness, **H** = hygiene/maintainability.

### felt-core (server) — ~2.5k lines of source, 135 tests, all passing

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| C1 | B | `brain.process_screen_context` | Each observation is saved as a `user` message in the chat session. This happens *before* the NONE check, so silent (mundane) observations are stored too. They take over the 20-message history window. |
| C2 | P | `brain.process_screen_context` | The privacy check covers `description` only, but `_cloud_chat(prompt, history, …)` sends the last 6 history messages. This is not the "window re-verified as a whole" rule that `_chat_reply` follows. |
| C3 | B | `api.history_endpoint` → dashboard | `/v1/history` returns observation rows. `App.tsx` maps history into chat bubbles without filtering. **Unverified in the UI**, but the code path is direct. |
| C4 | N | `brain.chat` | Router and privacy checks run one after the other; both are small-model round trips to the Nitro5. They are independent and could run concurrently. |
| C5 | N | `_PERSONALITY_PROMPT` | Doesn't say the reply will be *spoken*. Nothing forbids markdown, lists or emoji, and nothing strips them before TTS, so Piper reads `**` or bullet text literally whenever the model formats. |
| C6 | N | facts | Facts are only written by the explicit `remember_fact` skill, and *all* of them go into every local prompt without limit. There is no automatic memory, no conversation summary, and nothing beyond the last 20 messages. |
| C7 | H | `brain.chat` | `load_plugins()` rescans and imports the plugins directory on every message. `load_config()` rereads `.env` on every request. Both are cheap enough today, but they are unnecessary per-request work. |
| C8 | H | `brain.py` | The local-fallback `_ollama_chat([...personality + facts + history + prompt])` is written out three times; `process_screen_context` also imports inside the endpoint function. |
| C9 | H | `api.chat_ws` | Catches *every* exception and closes the socket without logging anything. |
| C10 | H | `api._synthesize_reply` | The reply text travels in an HTTP header (`X-Reply-Text`, percent-encoded). A long reply can go over proxy or server header limits. This works today, but it's fragile if replies get longer. |

### felt-animation (desktop) — ~720 lines, no tests

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| A1 | B/N | `_handle_reply` + main.gd `lipsync` | The mouth starts when the cues arrive, but the audio started earlier in felt-tray, so the mouth lags by the Rhubarb run time. |
| A2 | N | `_handle_reply` | Rhubarb, then `classify_reaction` (up to 15 s timeout), then `end_thinking_and_wait`, all in sequence. The first two are independent. The reaction gesture lands well after she has started talking. |
| A3 | N | ambient loop | Actions come every 20–45 s. In between she only idle-loops and blinks. There are no small in-between motions. |
| A4 | B/N | walk (`server.py` + main.gd `_process`) | No body rotation toward the direction of travel. Exponential `lerp` instead of constant speed, so the feet skate. The number of walk cycles (2–4, random) doesn't depend on the distance travelled. |
| A5 | H | `test_api.py` at repo root | An ad-hoc manual script, not a test. It belongs in `scripts/` or should be deleted. |
| A6 | H | logging | Logs only to the console, and the process runs hidden, so its logs are lost. felt-tray had the same problem; it now writes to `%TEMP%\felt-tray.log`. |
| A7 | N | expressions | An expression only comes from tag keywords. Lipsync visemes and `Fcl_ALL_Joy`, which has its own mouth, are added together with no arbitration, so a happy line can make the mouth shapes fight. |

### felt-tray (desktop) — ~800 lines, no tests

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| T1 | P | `watcher._capture_and_send` | Captures the whole primary monitor, *including Felt herself*, and relies on llava obeying the "don't transcribe private stuff" prompt. There is no process/app denylist *before* capture: KeePassXC, banking, email and so on are all captured and described. |
| T2 | N | watcher | Triggers only on a foreground-window change. Hours in one app (a game, one browser tab) mean no reactions at all, while a burst of alt-tabs is dropped by the lock. No dedup by window/process either. |
| T3 | B? | watcher | A single `mss.mss()` instance is created on the main thread and used from worker threads. mss documents instances as not thread-safe on Windows (GDI device contexts). It works today, so maybe fine for the current mss version. **Unverified.** |
| T4 | N | playback | No barge-in: pressing the voice hotkey while she's talking doesn't stop her. `winsound.PlaySound(None, SND_PURGE)` exists for exactly this. |
| T5 | H | `app.py` | The voice path and the screen path duplicate the "toast → play → POST reply_ready" block. |

### felt-vision (desktop) — 66 lines, no tests

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| V1 | H | repo | Empty README, no `.env.example`, config only through raw `os.environ` (no `.env` loading, unlike every other Felt repo). |
| V2 | N | model | `llava` (7B) on the desktop GPU, loaded whenever a window switch fires, including mid-game. It's slow, VRAM-heavy, and follows the privacy instruction poorly. Smaller vision models (moondream2, qwen2.5-vl:3b) are worth a comparison, with `keep_alive` tuned. |
| V3 | H | logging | Same console-only logging as felt-animation (A6). |

### felt-character-assets / Godot overlay

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| G1 | N | main.gd | No look-at / gaze system at all: not the VRM lookAt, not neck/eye bones. |
| G2 | H | main.gd `_unhandled_input` | Number-key test bindings and the `test/…` library match are unreachable in the click-through overlay: dead code. `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING` / `SMALL_TEST_WINDOW_FOR_TESTING` flags should be cleaned up too. |
| G3 | H | repo | 172 MB `.git`: PSDs plus the vrm addon's Linux/mac binaries are tracked. Acceptable, but LFS would be the tidy option if it keeps growing. |

### AnimToVrmaConverter

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| X1 | H | git | Four UniVRM/VRM `.unitypackage` files (~100 MB) and ~20 `unity_*.log` files are committed. |
| X2 | H/P | working tree | Uncommitted edits to `Convert-AnimToVrma.ps1` and `VrmaCliConverter.cs`. Untracked `Movement Animset Pro v1.693.unitypackage` is a **paid asset**: it must be gitignored, never pushed. |

### Cross-cutting

| # | Sev | Finding |
|---|-----|---------|
| Z1 | B | **No supervision.** Launch Felt starts four processes and nothing restarts them. felt-vision already died silently once this week and nobody noticed. There's no health indicator anywhere. |
| Z2 | H | Test coverage exists only in felt-core. The state machine in felt-animation (`state.py`) has already had one real race bug and is easy to unit-test with asyncio. |

---

## 3. Plan

Ordered by value and dependency. Each item has concrete steps. The sizes are
rough (S under 1 h, M a session, L several sessions).

### Phase A — fix what's broken (all S–M, no design debate needed beyond A3)

**A-1 · Take screen observations out of chat history** (C1, C3) — M
- Stop saving observations with `save_message`. Add a small
  `screen_observations` table (ts, description, reacted: bool) and keep the
  last ~5.
- `process_screen_context` builds its prompt from: the last few *real* chat
  messages + the last few observations as a separate system block ("Recently
  on screen: …").
- Normal chat also gets the latest observation as ephemeral context (only if
  it's less than ~2 min old). "What do you think of this?" then works, which
  it can't today.
- Only a reaction she actually *spoke* is saved as an assistant message, as it
  already is.
- One-time cleanup: delete existing `[System Observation:%` rows from
  `messages`. Destructive on the prod DB, so it needs Mario's explicit go.

**A-2 · Apply the privacy rule to the screen path** (C2) — S
- Either run `is_safe_for_cloud` over the same combined window
  (`_format_for_privacy_check(history, description)`), or send the cloud
  screen reaction *no* chat history at all, only observations.
  Recommendation: the second. A screen quip doesn't need the chat, and it
  removes the gap instead of adding another classifier call.

**A-3 · Put lips, voice and body in sync** (A1, A2) — M
- Move audio playback into felt-animation. felt-tray stops calling `play_wav`
  and just forwards the WAV (it already POSTs it to `/reply_ready`).
  felt-animation runs Rhubarb and `classify_reaction` **concurrently**
  (`asyncio.gather`), then starts audio + lipsync + expression + reaction at
  the same instant. It is the one process that knows all three timelines.
- Cost: speech starts later by the Rhubarb run time. Measure Rhubarb first on
  a typical 5 s reply. If it's over ~1 s, the alternative is amplitude-driven
  mouth movement in Godot (instant, cruder), with Rhubarb cues swapped in once
  they're ready. **This is the one real decision in Phase A.**

**A-4 · Walking that looks like walking** (A4) — M
- main.gd: replace `lerp` with `move_toward` at a constant speed that matches
  the walk clip (~1.2–1.4 m/s scaled to the rig; run ~2×). Turn her about 70°
  toward the travel direction over ~0.25 s before stepping and turn back to
  face the camera on arrival. Report `{"arrived": true}` over the relay.
- felt-animation: loop the walk cycle until `arrived` instead of a random
  2–4 repeats. The existing start/stop clips stay as bookends.

**A-5 · Supervision + visible health** (Z1, A6, V3) — M
- Add file logs for felt-animation and felt-vision, the same pattern as
  felt-tray.
- felt-tray's tray menu shows a live status line per component (core,
  animation, vision, voice), from a `/health` poll every 30 s, and restarts
  a dead local process (animation or vision) automatically, at most 3 times
  per 10 min.

**A-6 · Repo hygiene** (X1, X2, A5, G2) — S
- AnimToVrmaConverter: `git rm --cached` the logs and unitypackages, add a
  `.gitignore` (`*.log`, `*.unitypackage`, the paid asset explicitly), and
  review and commit the two modified scripts.
- Move `test_api.py` into `felt-animation/scripts/`. Strip the dead test
  input code from main.gd.

### Phase B — latency (the single biggest "feels alive" lever)

**B-1 · Measure first** — S
- Add per-stage timing logs to felt-core (`stt`, `router`, `privacy`, `reply`,
  `tts`) and felt-tray (request → first audio). Collect ~10 real turns.
  Nothing else in Phase B is prioritised until those numbers exist.

**B-2 · Cheap wins** — S
- Run the router and the privacy check concurrently (C4); they don't depend
  on each other.
- Set `keep_alive` on the Nitro5 router model so it never cold-loads. Keep the
  manual Ollama/ComfyUI swap rule intact; this only affects Ollama's own
  unload timer.
- Pre-render a handful of short filler lines in her voice ("hmm", "one sec",
  "let me see") and store them on the desktop. felt-animation plays one if
  the reply isn't back after ~2 s. That's an instant response for about
  30 KB of WAVs.

**B-3 · Sentence streaming** — L (biggest win, biggest change)
- felt-core streams the LLM output (Gemini and Ollama both support it), cuts
  it at sentence boundaries, runs TTS on sentence 1 while sentence 2 is still
  being generated, and pushes `{text, wav}` chunks over the existing
  WebSocket (`/v1/chat/ws` is already there).
- felt-tray/felt-animation keep a play queue; lipsync runs per chunk.
- Perceived latency drops to STT + router + first sentence + one TTS clip,
  instead of the whole reply.

**B-4 · TTS engine cost** — M, depends on B-1
- RVC's 3–8 s CPU step is probably the largest single cost. Options to
  compare: (a) keep Piper+RVC but run RVC on the Nitro5 GPU when ComfyUI isn't
  loaded; (b) evaluate a fast, natural single-stage TTS (e.g. Kokoro) and
  decide whether the Teto voice is worth the latency. That's Mario's taste
  call, done with a listen test.

### Phase C — presence and body language (Godot = presentation only; procedural motion counts as presentation)

**C-1 · Gaze** — M, very high value per effort
- Head and eyes follow the mouse cursor (`DisplayServer.mouse_get_position()`
  works even while the window is click-through). Use an additive rotation on
  the neck/head bones, clamped (±35° yaw, ±20° pitch), smoothed, with
  occasional small eye saccades. When the cursor has been still for a while,
  she looks back at the "camera" (at Mario).
- When she speaks she looks at the camera. When a screen reaction fires she
  glances at the screen area that changed, then back.

**C-2 · Idle micro-life** — S–M
- Split ambient into two layers: *micro* every 4–10 s (a head tilt, a weight
  shift, a glance) and *macro* every 40–90 s (walk, sit, stretch). The micro
  layer can be purely procedural in Godot, with no clips needed.
- Additive breathing on the chest/spine bones so she's never perfectly still.

**C-3 · Speaking body** — M
- While audio plays, layer small head nods and gesture accents timed to
  stressed syllables (use the density of Rhubarb's open-mouth cues as the
  rhythm), instead of one reaction clip before or after.
- Resolve expression vs viseme: while a viseme is active, scale down the
  mouth part of `Fcl_ALL_*` expressions. Alternatively, use the eye/brow-only
  `Fcl_EYE_*` / `Fcl_BRW_*` shapes for emotion while talking.

**C-4 · Emotion from the reply, not just the tag** — S
- `classify_reaction` returns `{tag, emotion, intensity}` in one call. The
  expression comes from `emotion`; the keyword map stays only as a fallback.

**C-5 · Presence awareness** — S
- Use `GetLastInputInfo` for AFK detection: after ~10 min idle she gets
  sleepy or sits down; when input resumes she perks up, and after a long AFK
  she gives a short greeting (it goes through the initiative budget, D-3).
- Fullscreen detection: when a fullscreen app is in the foreground she moves
  to the edge, or optionally hides.

### Phase D — conversation naturalness (felt-core)

**D-1 · Speak like speech** — S
- Add to the personality prompt: "Your reply is spoken aloud. No markdown, no
  lists, no emoji, no URLs; say numbers the way a person would." Also add a
  `strip_for_tts()` safety net in `_synthesize_reply` (C5).

**D-2 · Real memory** — M
- Automatic fact extraction after each exchange: a local model, local only,
  proposes 0–2 durable facts, deduped against the existing ones.
- A rolling conversation summary, refreshed every ~20 messages, so context
  reaches further back than 20 turns.
- Fact retrieval by relevance (a small embedding index) instead of putting
  every fact into every prompt (C6).

**D-3 · One initiative budget** — M. *Superseded for screen reactions by R-5
below: they're always spoken, and the budget limits frequency, never
silence.*
- Everything she says unprompted (screen reactions, email pings, alerts, AFK
  greetings, future idle chatter) goes through a single governor in
  felt-core, for example: max 1 unprompted remark per 10 min, none while Mario
  is speaking or a mic is in use, fullscreen only for "dramatic" events.
  Without this, every new proactive feature makes her more annoying, not
  more alive.

**D-4 · Screen awareness v2** (T1, T2, V2) — M
- Denylist by process *before* capture (KeePassXC, banking/email/password
  managers, a configurable list). The screenshot never exists for those apps.
- Exclude the Felt overlay from the capture: hide her window from capture
  with `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` on FeltOverlay, a
  one-line Win32 call in the click-through patch.
- Triggers: window switch (debounced ~3 s so alt-tab bursts settle) plus a
  slow periodic sample every 3–5 min while in the same window, deduped by
  process + title + phash.
- Compare moondream2 / qwen2.5-vl:3b against llava for speed, VRAM and
  instruction-following.

**D-5 · Barge-in** (T4) — S
- The voice hotkey while she's speaking stops the audio, lipsync and the
  current reaction, then starts listening. (After A-3 this lives in
  felt-animation.)

**D-6 · Hands-free follow-up** — L, later
- After she replies, a ~6 s VAD window accepts a follow-up without the
  hotkey. Full wake word ("hey Felt", openWakeWord) is the next step after
  that. Both need mic-privacy UX (a visible "listening" state) designed first.

### Phase E — code health

**E-1 · Tests where the bugs have been** — M
- felt-animation: the `state.py` thinking/lock race, `resolve_posture_tag`,
  `classify_reaction` validation, `_known_tags_under`, `_expression_for_tag`.
- felt-tray: `api_client` header decoding, `playback` (the temp-file path).
- felt-vision: `/analyze` with a mocked Ollama.

**E-2 · felt-core tidy** — S
- Cache the plugin registry (reload only when `plugins/` changes), deduplicate
  the local-chat builder (C8), log in `chat_ws` (C9), and move the reply text
  from the header into a multipart/JSON body alongside the audio (C10), which
  B-3 streaming replaces anyway.

**E-3 · felt-vision to Felt standards** — S
- README, `.env.example`, `python-dotenv` config like the siblings, file
  logging.

---

## 4. Recommended order

1. **A-1, A-2** — memory and privacy bugs, server side, one deploy.
2. **B-1** — instrument latency, so everything after this is prioritised by
   real numbers.
3. **A-3** — sync voice, lips and body (after measuring Rhubarb).
4. **C-1 gaze + C-2 micro-life + A-4 walking** — the biggest visual
   "she's alive" jump.
5. **D-1, B-2, D-5** — quick conversational wins.
6. **A-5, A-6, E-*** — supervision and hygiene, fitted in between.
7. **B-3 streaming, D-3 initiative budget, D-4 screen v2, D-2 memory** — the
   larger builds.
8. **B-4, C-3, C-5, D-6** — after the above settles.

## 5. Couldn't verify from here

- How many rows of the live `messages` table are observations. The query
  against the production DB was blocked by the permission classifier; the
  code path alone is conclusive for the bug itself.
- Real per-stage latency, Rhubarb run time on a typical reply, and whether
  mss cross-thread use (T3) actually misbehaves.
- Whether the chat window visibly shows observation bubbles (C3). The code
  says yes; one look at the window confirms it.

---

# Round 2 — snappier, livelier, skill replies (2026-09-22, same day)

Mario's direction: "further look into how to make her lively and alive,
especially how she handles skill replies, like weather, maybe run it through
Gemini … latency metric and cache of some stuff … ways to make her snappier
and more natural." Mid-review: **"I want screen reactions to be spoken
aloud, that's the whole point of having them."** Still plan-only, nothing
implemented.

## 6. What the numbers actually say (measured, not guessed)

Two probe messages went to `/v1/text-chat` (session `latency-probe`), and the
stage timings came from felt-core's timestamped server logs. Screen-reaction
timings come from the last ~20 h of real traffic.

| Turn | Stage | Time |
|------|-------|------|
| "what's the weather like right now?" | router LLM (qwen2.5:1.5b, Nitro5) | ~3.8 s |
| | Open-Meteo fetch | **0.29 s** |
| | skill reply, local llama3.1:8b | **17.4 s** |
| | TTS (Piper + RVC) of that reply | **12.0 s** |
| | **total, before felt-tray even starts playback** | **33.4 s** |
| "tell me something fun about octopuses" | router → **misrouted to `generate_image`** | ~4.9 s |
| | ComfyUI job submitted, polled until timeout | ~48 s |
| | local reply (llama3.1:8b) | 58 s |
| | TTS | 25 s |
| | **total** | **136 s** |
| screen reaction, Gemini path | Gemini flash-lite reply | 0.55–0.77 s |
| screen reaction, local path | llama3.1:8b reply | 4.7–5.2 s |
| | TTS (short line) | 2.2–3.4 s |

What this shows:

1. **The weather API is not the problem (0.29 s).** Caching the Open-Meteo
   call on its own saves almost nothing. The time goes into the *local LLM
   phrasing the result* (17 s) and *TTS of a long reply* (12 s).
2. **The Nitro5 GPU is over-subscribed.** Read-only `nvidia-smi` after the
   probes: ComfyUI (a long-running manual process) holds 2.25 GB, Ollama
   2.5 GB, 4.8 of 6 GB in use. llama3.1:8b needs ~5 GB, so it's partly offloaded
   to CPU whenever ComfyUI is resident. That's the likeliest root of the 17–58 s
   local replies. The manual Ollama/ComfyUI swap rule stands; nothing was
   touched.
3. **Gemini is ~25× faster than local** for the phrasing step (0.6 s vs 17 s).
4. **Reply length drives TTS time.** The weather reply produced ~0.8 MB of
   WAV, a long, rambly answer to "what's the weather". TTS time grows with
   reply length.
5. **Router bug:** "tell me something fun about octopuses" went to
   `generate_image` and started a real ComfyUI job. Nothing in the message
   asks for an image.
6. **Screen reactions were effectively always silent on the cloud path.** 11 of
   11 Gemini-routed observations answered NONE. All 7 local-routed ones spoke,
   which is also why "sometimes she talks, usually not".
7. **Weather reaction tags don't exist.** `get_weather` emits
   `reaction/weather/{sun,rain,storm,snow}` (plus the `reaction/weather`
   default in `plugins/tags.json`). The library has no `reaction/weather`
   folder at all (only `failure`, `listening`, `stumble`). felt-animation
   skips its own classifier whenever a tag is supplied, plays the missing tag,
   gets no `finished` notice, and **holds the activity lock for the 30 s
   CLIP_TIMEOUT**. So every weather answer means no gesture and ambient frozen
   for 30 s. The skill's comment says "the fallback lookup (felt-overlay side)
   gracefully broadens", but main.gd explicitly does no broadening.

## 7. Round-2 plan

### R-1 · Skill replies through Gemini when the skill's output is public data — M

Today every tool-result reply is forced local (brain.py: "tool output can
carry real personal data"). That's right for email or calendar, but overly
broad for weather.

- Add a `privacy` field per skill (in the skill module, or a
  `plugins/skills.json` next to `tags.json`): `"public"` or `"private"`,
  **default private**, so a new skill fails closed.
- **Decided (Mario, 2026-09-22):** "Google already has my email and calendar
  so that's fine, same with alarm, shopping list and music."
  - `public` (cloud-phrased): `get_weather`, `get_time`, `news_digest`,
    `web_search`, `poe_price_check`, `generate_image`, `check_email`,
    `list_calendar_events`, `create_calendar_event`, `set_alarm`,
    `set_timer`, `list_alarms`, `cancel_alarm`, `shopping_list`,
    `play_music`, `media_control`.
  - `private` (stays local): `search_documents` (includes Obsidian, not only
    Drive), `smart_home_control`, `remember_fact`, `find_phone`,
    `get_phone_battery`, `get_container_status`, `get_recent_alerts`,
    `get_gpu_status`, `printer_status`, `delegate_research`, plus any new
    skill until it's explicitly marked public.
  - The same change applies elsewhere, or these skills still get pulled back
    local: `privacy.py`'s `_PRIVACY_PROMPT` currently lists "the contents of
    emails, calendar events" as PRIVATE. It needs updating to match, or a
    follow-up question about an email in the recent history fails the
    whole-window check and falls back to local. The email-summary path
    (`_summarize_pending_email`, currently hardwired local) moves to Gemini
    too.
- Public-skill reply → Gemini with the personality prompt + the tool result.
  Recent chat context only if it clears the existing whole-window privacy
  check, and never facts. Local fallback if Gemini fails.
- New phrasing instructions for *all* skill replies (both paths): "one or two
  spoken sentences, lead with the answer, then one bit of personality (an
  opinion, a suggestion, a callback)". Example target: *"Fifteen and
  drizzly — honestly a perfect excuse to stay in."* Not *"The current weather
  conditions are…"*. Shorter replies also cut TTS time roughly in proportion.
- Local path gets `num_predict` (~80 tokens) as a hard cap, so a slow local
  reply can't also be a long one.
- `SkillResult.voice_line` already exists and nothing reads it. Wire it up so
  a skill can supply a spoken form distinct from its displayed text (e.g. poe
  prices: short spoken summary, full listing in the toast/chat).

Expected: weather goes from ~33 s to about router 3.8 + fetch 0.3 + Gemini
~0.7 + TTS of a short line ~2.5 ≈ **7 s**, before any caching. R-3 takes most
of the rest out.

### R-2 · Latency metrics, so every later decision uses real numbers — S–M

- A `timed("stage")` context manager in felt-core wrapping each stage
  (`stt`, `router`, `privacy`, `skill:<name>`, `reply:<cloud|local>`, `tts`).
  Rows go into a `latency` table: `(request_id, ts, endpoint, stage, ms,
  route, skill, chars)`.
- The same numbers come back in a standard `Server-Timing` response header.
  felt-tray logs them plus its own client-side stages (upload, playback start),
  so each turn gets one line: *"hotkey release → first audio: 7.2 s (stt 0.9,
  router 3.8, …)"*.
- `GET /v1/metrics/latency?since=24h` returns p50/p95 per stage, and a small
  panel in felt-dashboard shows it. This also answers "is the Nitro5 in the
  ComfyUI state right now?" at a glance, because local reply time jumps.
- Probe sessions (`latency-probe`) are excluded from history and the UI.

### R-3 · Caching and precomputing: where the time really goes — M

Mario's instinct (cache the weather for 12 h) points at the right thing. But
the fetch is 0.3 s; the cost is the *phrasing + TTS*. So cache further down
the pipeline:

- **Weather data**: cache the Open-Meteo response. Current conditions are
  fresh for **15–30 min** (Open-Meteo refreshes current data every 15 min).
  The daily forecast part is fine for 1–3 h. 12 h is too stale for "right
  now": a morning fetch would answer an evening question with the morning's
  temperature. A background refresh keeps it always warm, so a request never
  waits.
- **Precomputed spoken answers (the real win)**: every refresh, a background
  task also builds the "current weather" line through Gemini and **pre-renders
  its TTS**. "What's the weather?" becomes router time + returning a cached
  WAV, about 4 s today and under 1 s with R-4. Same for "what time is it"
  (template, not an LLM) and possibly a daily news headline. Invalidated
  whenever the underlying data changes.
- **TTS cache on felt-voice**: `hash(text, voice, rvc_model)` → WAV on the
  Nitro5 disk. It pays off for filler lines, "I didn't catch that", greetings,
  and precomputed answers.
- **Filler/acknowledgement clips**: a dozen short in-voice lines ("hmm", "one
  sec", "let me check", "ooh, okay") pre-rendered once and stored on the
  desktop. felt-animation plays one immediately when a request passes ~1.5 s,
  or right away for a known-slow skill (web search, image, research). That's
  an instant response with no server round trip.
- **Router cache**: the router runs at temperature 0, so the same normalized
  message + same skill registry always gives the same decision. A small LRU
  cache saves the ~4 s on repeated phrasings ("what's the weather", "pause
  the music"). Same for privacy verdicts.
- **Keep models warm**: `keep_alive` on the router model so it never
  cold-loads. This only affects Ollama's own unload timer and doesn't
  interfere with the manual swap.

### R-4 · Cut the router's 4–5 s — M

- **Deterministic fast path** before the LLM router, for unambiguous intents
  only: a word-boundary match on `weather|forecast|rain(ing)?` → `get_weather`,
  `what time` → `get_time`, `pause|skip|next song|volume` → `media_control`.
  Anything ambiguous still goes to the LLM router. This takes the most common
  voice commands from ~4 s to ~0 ms.
- Run the router and the privacy classifier **concurrently**. Right now
  they're sequential, and privacy is only needed if the router says "no skill".
- **Guard expensive or side-effect skills**: `generate_image` only runs if the
  message contains an explicit make-verb (draw, generate, make, create, paint +
  image/picture). Otherwise it's treated as plain chat. That fixes the octopus
  misroute without another prompt example, which the router prompt already
  has plenty of.

### R-5 · Screen reactions are spoken — M

Per Mario, the point is hearing her react. Redesign:

- **Remove the NONE option.** Every screen-reaction call produces a short
  spoken line (one sentence, in character, never "I see your screen shows…").
- **Frequency comes from rules, not the model**: at least ~2 min between
  spoken screen reactions (tunable). Dedupe by process + window title: a new
  tab in the same browser doesn't count as new, a different app does. Skip
  while Mario is talking to her or she's mid-reply. All of this goes through
  the initiative budget (D-3), so screen, email and AFK remarks don't pile up.
- **Private screens**: stop them before capture with the process denylist
  (D-4: KeePassXC, banking, email). If a private screen still gets through,
  the line must not reference its content.
- **Quality**: the reaction prompt gets the last 2–3 observations as context,
  so she can notice continuity ("still on that boss, huh?") instead of
  reacting to each screenshot cold. Gemini path by default, since the
  description is already the privacy-filtered artefact.
- **Fastest path**: a Gemini reply (~0.7 s) + a short-line TTS (~2.5 s) takes
  3–4 s from description to voice, fine for a remark nobody asked for. The
  vision step itself (llava on the desktop) isn't measured yet (R-2).

### R-6 · Make skill replies *feel* alive, not just faster — S–M each

- **Skill-specific "working" body language** while waiting: time → glance at
  her wrist, weather → look up/out, search/research → a "typing" or thinking
  pose, image → a hands-together "ooh" anticipation pose. Driven by the
  router's decision, sent to felt-animation as soon as the skill is chosen,
  before the reply exists. A cheap early signal, which needs a
  `/request_progress {skill}` hop.
- **Tag validation + broadening in felt-animation**: an incoming tag that isn't
  in `known_tags` is broadened (`reaction/weather/sun` → `reaction/weather` →
  `reaction`). If nothing matches, it falls through to `classify_reaction`
  instead of the 30 s dead wait. This fixes finding 7 and every future
  "felt-core tag vs desktop library" drift.
- **Weather clips**: either add real `reaction/weather/{sun,rain,storm,snow}`
  clips (from the sources in "Asset sourcing" below), or
  remove those tags from the skill. Broadening covers it either way.
- **Emotion from the phrased reply**: public skill replies go through Gemini
  anyway, so ask for a structured `{reply, emotion}` in the same call (JSON
  mode), which costs no extra round trip. The emotion drives the expression.
- **Weather-aware presence**: the first time Mario becomes active in the
  morning (AFK → active, C-5), she gives a one-line greeting with the
  precomputed weather line. It's pre-rendered, so it plays instantly, and
  counts against the initiative budget.
- **Callbacks**: the reply prompt for public skills includes the last ~3
  exchanges, so "and tomorrow?" after "what's the weather" works naturally
  and she can say "still raining, told you".

### R-1b · Refinement: gate the *result*, not the skill (Mario, 2026-09-22)

> "if we can get a slow model that then hits gemini it's fine, stuff like
> your shelf light is on isnt private, but fetching the data is"

This replaces most of R-1's per-skill list:

- **Fetching stays local, always.** Skills already run inside felt-core on the
  server. Gemini never calls APIs, reads files, or touches devices. Nothing
  about this changes.
- **Phrasing goes to Gemini by default.** The skill's result text goes through
  the local privacy classifier. SAFE → Gemini phrases it (~0.6 s). PRIVATE →
  local model phrases it. "Your shelf plug is on" is SAFE; a paragraph of a
  health document isn't.
- **No check needed** for the public-data skills (weather, time, news, web
  search, PoE, image) or the Google-already-has-it ones (email, calendar,
  alarms, shopping list, music): straight to Gemini.
- **Hard-local, never sent** even if the classifier says SAFE, because the
  result *is* the private data and a 1.5B classifier can misjudge:
  `search_documents` (Obsidian/Drive contents), `remember_fact` / facts,
  `find_phone` (location). Everything else (smart home, phone battery,
  container/alerts/GPU status, printer, research) goes through the result
  check.
- **The router gets the same treatment.** The raw message goes through the
  privacy check *first*. SAFE messages are routed by Gemini with native
  function calling: one ~0.6 s call, far more accurate than qwen2.5:1.5b, and
  it fixes misroutes like the octopus → generate_image one. PRIVATE messages
  use the local router as today. The local LLMs then mostly just
  *classify* (SAFE/PRIVATE, a tiny prompt with a one-word answer), and a slow
  box is fine for that job.
- Resulting skill turn (e.g. smart home): privacy(msg) ~1–2 s local → Gemini
  route 0.6 s → skill → privacy(result) ~1 s local → Gemini phrase 0.6 s →
  TTS. Roughly 5 s plus TTS, against ~25 s today. Measure with R-2.

### R-8 · Offload node: the Redmi Note 9 Pro — **DROPPED**

Mario, 2026-09-22: "skip phone, I would prefer if it didn't explode" (an
always-on phone on a charger and a battery with no charge limit). Kept below
for the record only.

Mario has one lying around (Snapdragon 720G: 2 fast + 6 efficiency cores,
Adreno 618; he estimates ~4 GB RAM). Honest expectations before
benchmarking:

- **LLM only on CPU.** llama.cpp's GPU/Vulkan path on an Adreno 618 isn't
  worth it. Generation is probably single-digit tokens/s for a 0.5–1.5B q4
  model, but the real problem is **prompt processing**: probably tens of
  tokens/s. The router prompt is ~2.5k tokens, so uncached that's minutes.
  Only viable with `llama-server` **prefix caching** (the static system prompt
  is processed once and kept in the KV cache; each request then only processes
  the new message + a few output tokens). That makes a fixed-prompt, one-word
  classifier the best-suited job: the privacy check, not the router, and never
  free-form phrasing.
- **Fit with R-1b**: once Gemini does routing and phrasing for SAFE traffic,
  the local work is mostly that classifier. A phone running it frees the
  Nitro5 from everything except fallback phrasing, so ComfyUI time stops
  mattering for most turns.
- **Always-on phone risks**: a battery kept at 100 % on the charger swells
  over months. Without root, the Note 9 Pro has no charge limit. Fix: put it on
  a Home Assistant smart plug and cycle it 40–80 % by the phone's reported
  battery level. Android also kills background Termux: it needs
  `termux-wake-lock` and battery optimisation disabled (the non-root debloat
  method from the Poco X7 Pro applies).
- **Step 1 is a 10-minute benchmark, not a build.** Termux →
  `pkg install llama-cpp` → download qwen2.5-0.5b and 1.5b q4 GGUFs → run
  `llama-bench` for prompt-processing and generation speeds, then run the
  real privacy prompt with a warm cache. Those numbers decide whether it
  becomes the classifier node or stays in the drawer.
- Not a candidate: TTS/RVC (RVC is the slow part and needs more than this),
  STT (the Nitro5 is fine), vision.

### R-7 · The Nitro5 decision (Mario's call)

*Mostly defused by R-1b: local models become classifiers plus a fallback
phrasing path. The 3B-for-private-phrasing idea below still applies to that
fallback.*

The local model doesn't fit in VRAM while ComfyUI is loaded, and that's the
floor under every local reply. Options, with the manual-swap rule untouched:

- (a) Switch felt-core's local chat model to a ~3B model (llama3.2:3b /
  qwen2.5:3b, ~2 GB) that fits *alongside* ComfyUI. Local replies get faster,
  somewhat dumber. Private skills are mostly "state this fact nicely", which a
  3B model handles fine.
- (b) Keep 8B and accept slow local replies whenever ComfyUI is resident,
  relying on R-1 to send most traffic to Gemini.
- (c) Both: 3B for private skill phrasing (short, factual), 8B only for
  private free conversation.

Recommendation: (c), measured through R-2 before and after.

## 8. Round-2 recommended order

1. **R-2 metrics** first (small, and everything else gets judged by it).
2. **R-6 tag broadening** plus **R-4 generate_image guard**: two real bugs,
   both small.
3. **R-1 Gemini for public skills + short spoken phrasing**: the biggest
   single latency and liveliness gain for skills.
4. **R-5 spoken screen reactions**, together with Phase A's A-1/A-2 (memory
   and privacy fixes on the same code path).
5. **R-3 caching/precompute + filler clips**, then **R-4 fast path**.
6. **R-7** once the metrics show the before/after.
7. **R-6 remainder** (working poses, emotion, morning greeting) alongside
   Phase C.

Side effect of this review, for the record: the octopus probe submitted one
real `generate_image` job to ComfyUI on the Nitro5 (the router misroute
above). Nothing else was triggered, and both probe turns are stored under
session `latency-probe`, separate from the `dashboard` conversation.

---

# Round 3 — interaction and movement (2026-09-22)

Mario: "what else can we do regarding interactions and movement with Felt?"
Plan-only. It builds on Phase C (gaze, micro-life, speaking body, emotion,
presence) and A-4 (walking), which are not repeated here.

**Ground truth this round is built on** (checked in the code / library):
- The overlay is **whole-window click-through**: `WS_EX_LAYERED |
  WS_EX_TRANSPARENT` via `patch-clickthrough.ps1`. She can't be hovered,
  clicked or dragged at all today.
- Godot plays **one clip at a time** through `AnimationPlayer.play()`. No
  layering, so she can't gesture while walking or breathe on top of a pose.
- Position is **x only**. Feet are clamped to `FLOOR_Y = 0` every frame, and
  she lives on the primary monitor only (`LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING`).
- Spring bones (hair/skirt physics) are **on**, so any movement gets free
  secondary motion.
- Library: 73 clips. It has idle, sitting, stand↔sit, one walk cycle, run,
  ambient (look_around, pose, show_off, stretch ×2, weight_shift), emotions
  (angry, embarrassed, happy, laughing, sad, sighing, surprised), gestures
  (finger_gun, nodding, pointing, shaking_head, shrugging, talking(+sitting),
  thinking, wave), greeting, dance, sleepy/yawn, reaction/{failure, listening,
  stumble}. **Missing**: turns, walk start/stop (the code references
  `start_walking`/`stop_walking` tags that don't exist), ledges, falling,
  landing, grabbed/dangling, pats/pokes.
- **Bug-level finding:** felt-tray fires `/request_started` when voice
  recording *starts*, so she plays "thinking" while Mario is still talking.
  `reaction/listening` exists and is never used.

## I-1 · Listening that looks like listening — S

- Hotkey pressed → a new `/listening_started` → `reaction/listening` (looping
  until stop) + gaze locked to camera + a slight head tilt.
- Hotkey released → `/request_started` → thinking (as now).
- **Backchannel nods**: felt-tray already has the mic stream, so compute an
  RMS level. When Mario pauses for ~400–700 ms mid-sentence, send a `nod` pulse
  (a small additive head nod, or `gesture/nodding` at low weight). This is
  what makes it feel like someone listening rather than a recorder.
- The same applies to typed chat: while the chat window has focus and he's
  typing, she glances toward it.

## I-2 · Touchable Felt: selective click-through — M (foundation for I-3/I-4/I-5)

The window stays click-through *everywhere except her silhouette*:

- Godot projects a few bones (head, chest, hips, hands, feet) to screen space
  every ~50 ms and sends a coarse hitbox (a head circle + a body capsule +
  limb capsules) over the relay: `{"hitbox": {...}}`.
- felt-animation (Python, `ctypes`) polls `GetCursorPos`. When the cursor is
  inside the hitbox it clears `WS_EX_TRANSPARENT` on FeltOverlay's HWND.
  `patch-clickthrough.ps1` already sets it cross-process, so the same call
  works in reverse. It restores the flag the moment the cursor leaves.
- **Failsafe**: the default state is transparent. If felt-animation or the
  relay dies, a Godot-side watchdog re-applies full passthrough, so the
  overlay can never end up eating clicks across the whole screen.
- Hover alone: gaze snaps to the cursor, she does a small "hm?" look, and a
  soft cursor-change hint shows (optional).

## I-3 · Poke, pat, tickle — S–M (needs I-2)

- Hit zones from the same hitbox. **Head**: a click is a pat, and holding and
  moving the cursor across it is petting: eyes close (`Fcl_EYE_Joy`), happy
  expression, a lean-in, and a pre-rendered happy sound. **Body**: a poke gets
  a flinch and "hey!". **Repeated pokes escalate**: surprised → annoyed → angry
  → she walks away from the cursor, with a cooldown before she forgives.
- **Instant, no LLM**: responses are pre-rendered clips + cached TTS lines
  (R-3's TTS cache), picked with variety and repeat-avoidance. Latency is 0.
- These count as user-initiated, so they don't use the initiative budget. They
  feed the mood state (I-7): pats raise affection, spam lowers patience.
- New clips needed: head_pat_receive, flinch/poked, a "walk away huffily"
  variant (or reuse walk with angry expression).

## I-4 · Pick her up, drag, drop, throw — M (needs I-2, y-movement)

- Mouse-down on her body and moving → "grabbed": a dangling/struggling clip,
  position follows the cursor (x **and y**). Hair and skirt swing for free from
  the spring bones.
- Release → she falls with simple gravity (+ the throw velocity from the last
  few cursor samples) → a landing clip scaled to the fall height (small: soft
  land; large: `reaction/stumble` + a grumble line). Dropped onto a window edge
  (I-5), she lands *there*.
- Requires replacing the hard `FLOOR_Y = 0` clamp with a variable "ground
  height", which I-5 needs anyway.
- New clips: falling idle, soft landing, hard landing, dangling/struggling.

## I-5 · The desktop is her world (Shimeji-style) — L, the headline feature

- felt-animation enumerates visible top-level windows (`EnumWindows` +
  `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)`, skipping
  cloaked/minimized/tool windows) plus the taskbar rect, ~4×/s. It sends them
  to Godot as "platforms" in world units (the orthographic camera makes the
  pixel→world mapping a straight linear transform).
- Behaviours, chosen by felt-animation's ambient/mood logic, not Godot:
  - **Sit on a window's top edge**, legs dangling (ledge-sit clip + idle).
  - **Walk along the taskbar** / along a window's top edge.
  - **Peek** in from the screen edge or from behind a window corner.
  - **The window moves** → she rides it (and wobbles with spring bones).
    **It's minimized or closed** → she falls (I-4) → lands → an annoyed line
    ("rude").
- Courtesy rules: never park over the focused window's content, avoid
  fullscreen apps entirely (C-5), prefer non-focused window edges and the
  taskbar, and move out of the way when the cursor approaches with purpose
  (fast movement toward her).
- Depends on: I-4 (falling/landing), y-movement, turns, and a ledge-sit clip.
  Foot IK is nice-to-have for sloped/uneven edges (not needed for flat window
  tops).

## I-6 · Cursor play — S (needs gaze C-1)

Low frequency, mood-gated:
- When the cursor idles near her, she occasionally reaches toward it or bats at
  it.
- Fast circles around her make her dizzy (a wobble + dizzy expression).
- Rarely, when bored (I-7), she walks over to where the cursor has been
  resting, curious.

## I-7 · Mood and energy: one state that makes everything coherent — M

- felt-animation keeps a persistent mood vector `{energy, happiness, boredom,
  affection}` (saved to disk, partly reset each morning). It drifts over time
  and is nudged by events: pats (+affection), pokes spam (−patience), being
  ignored for hours (+boredom), good conversations (+happiness), late hours
  (−energy).
- **It drives**:
  - ambient action weights (bored → more wandering, sighs, and looking at the
    screen; low energy → sitting, yawning)
  - which idle/walk variant plays (tired trudge vs happy skip, once those clips
    exist)
  - walk speed
  - a subtle *resting* expression baseline
  - screen-reaction tone
- **It's sent to felt-core** as one line in the personality prompt ("Current
  mood: a bit sleepy, pleased Mario patted her earlier"), so the voice
  matches the body.
- Lives in felt-animation/felt-core, per the Godot-is-presentation-only rule.

## I-8 · Daily rhythm — S (needs I-7)

A schedule table in felt-animation:
- Morning: stretch + the pre-rendered weather greeting when Mario first
  becomes active (R-6).
- Midday: a "did you eat?" nudge (budgeted).
- Evening: winding down.
- After ~1 am: increasingly sleepy, yawns, and a gentle "go to bed" on a long
  cooldown.
- Weekday and weekend variants. All unprompted speech goes through the
  initiative budget (D-3).

## I-9 · Context-aware behaviour — M

- **Typing**: the keystroke *rate* only (a low-level hook that counts events
  and never records keys) → she settles down, sits, and keeps quiet. After a
  long focused stretch, she suggests a stretch break (budgeted).
- **Music playing** (desktop audio loopback via WASAPI, onset/beat
  detection with `aubio`, nothing stored or sent anywhere): her head bobs on
  the beat, and occasionally she does a short `dance` if mood is high. Spotify's
  audio-features API is closed to new apps, so this has to be local beat
  detection.
- **In a call** (another app using the mic, e.g. Discord voice): quiet mode.
  She sits, doesn't speak, and holds back screen reactions.
- **Gaming**: fullscreen detection (C-5) → retreat to the corner, or hide
  entirely (Mario's choice). For games in borderless windows, a process list
  of known games does the same.

## I-10 · Voice + body as one — S–M

- **Non-verbal sounds**: a yawn sound synced to the `sleepy/yawn` clip, a
  giggle with `emotion/laughing`, a sigh with `emotion/sighing`, a "hm?" on
  hover. Pre-rendered once, played by felt-animation at the clip's start.
  Cheap, and one of the biggest "she's real" signals.
- **Emotional delivery**: Piper's `length_scale` per emotion (excited →
  faster, sleepy/sad → slower), using the emotion from R-6's `{reply,
  emotion}` result. RVC keeps the voice identity.
- **Pointing at what she's talking about**: when a screen reaction fires, she
  turns toward the foreground window's rect and uses `gesture/pointing` or a
  glance. The window rect comes from I-5's enumeration. The vision model
  isn't needed for *where*.

## I-11 · Movement quality underneath all of this — M–L

- **AnimationTree with layers** instead of a single `AnimationPlayer.play()`:
  a base state machine (idle / locomotion / sit / ledge / fall) + an additive
  upper-body layer (talking gestures while walking, waving while sitting) + an
  additive procedural layer (gaze, breathing, backchannel nods). This is the
  prerequisite for most of the above to look good together.
- **Locomotion**: turn-in-place clips (left/right 90°), walk start/stop, and
  speed-matched movement (A-4). Root-motion clips are a later upgrade for zero
  foot sliding.
- **Variants driven by mood**: sneak, happy skip, tired trudge.
- **Second monitor**: drop `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING`, and let her
  walk across to the 1080p screen (a window spanning both, or a "hop" at the
  edge). Later.

## Clip shopping list (see "Asset sourcing" below for where each comes from)

Turn left 90 / turn right 90 · start walking / stop walking · happy skip ·
tired walk · sneak walk · sitting on ledge + ledge idle · falling idle · soft
landing · hard landing · dangling/struggling (grabbed) · head-pat receive ·
flinch/poked · dizzy · reaching up / batting at something · typing (for R-6
working pose) · looking at wrist (R-6) · head-bob / music groove loop ·
cheering (game wins).

## Round-3 decisions (Mario, 2026-09-22)

> "I like a lot of those, except the pats and touchable skip that. Issue is
> actually getting animations and sound effects, you gonna have to figure
> that one out. but especially the desktop as her world and daily rhythm and
> context aware with music and stuff, tho never keep her truly quiet, that's
> no fun, maybe if someone is yapping on discord she doesn't talk over unless
> prompt?"

- **Dropped**: I-2 touchable, I-3 pats/pokes, and **I-4 drag/drop** (it needs
  I-2, since you can't grab what you can't click). The overlay stays fully
  click-through. Falling and landing clips are still wanted: I-5 needs them
  when a window she's on gets closed or minimized.
- **Priorities**: I-5 desktop world, I-8 daily rhythm, I-9 context awareness
  (music especially). I-1, I-6, I-7, I-10, I-11 stay as supporting items.
- **Never truly quiet** (revises I-9):
  - *Typing*: she settles and moves less, but still talks. The frequency of
    unprompted remarks drops a bit.
  - *Discord / calls*: detect **someone actually speaking**, not "a call is
    open". Use a per-process audio session peak meter on Discord's output
    (`pycaw` → `IAudioMeterInformation` for the Discord session; also works for
    Teams/Zoom). While the peak is above the voice threshold (plus ~1.5 s hang
    time), unprompted remarks are **held**: queued for a few seconds, then
    dropped if they're stale. They go out in the next lull. Prompted replies
    (hotkey or typed) always go through immediately. Her body stays fully
    lively, with no forced sitting or hiding.
  - *Gaming fullscreen*: she moves out of the way (C-5), and remarks follow
    the normal budget.

## Asset sourcing: animations and sounds (Mario: "you gonna have to figure that one out")

### What's already on disk and unused (checked 2026-09-22)

- **Movement Animset Pro, 208 clips already converted to `.vrma`**, sitting
  loose in `AnimToVrmaConverter/` and not in the library. It covers most of
  I-5/I-11's locomotion list:
  - **Turns**: `TurnLt90_Loop`, `TurnRt90_Loop`, `TurnLt180`, `TurnRt180`,
    `RunStrafeUpdate_Turn180Surprised`.
  - **Walk**: `WalkFwdStart`, `WalkFwdStart90_L/R`, `WalkFwdStart180_L/R`
    (turn-and-go), `WalkFwdStop_LU/RU`, `WalkFwdLoop` (+`LeanL/R`,
    `WalkArchLoop_L/R` for curved paths), backwards walk.
  - **Run**: the same start/stop/turn set, plus sprint.
  - **Air**: `FallingLoop`, `JumpIdleStart`, `JumpIdleLand`,
    `JumpIdleLandHard`, and the walk/run jump variants. That covers "window
    closed under her → fall → land" and hopping between windows.
  - **Climb**: `RunStrafeUpdate_Climb1m`, `SlideClimb_Climb2m`, `Vault1m` →
    climbing *onto* a window edge.
  - **Getting up**: `GetUpFromBack`, `GetUpFromFace` (after a hard landing).
  - **Sitting**: `SitChairStart/Loop/End`.
  - **Misc**: `DontKnow` (shrug), `KeypadUse_*` / `ButtonPush_*` (a "working"
    pose for R-6), `PickUp_*`, `Crouch_*` (peeking), `Idles_Idle2..6` (idle
    variety).
  - **Caveat**: generic, fairly masculine mocap gait. Fine for turns, falls,
    climbs and transitions. For her main walk, keep the current feminine
    walk, or source one from the libraries below. Also check the pack's
    licence covers personal use in this project; Unity Asset Store packs
    normally allow use in any of the buyer's own projects.
  - **Action**: triage the 208 into the library's tag folders (e.g.
    `locomotion/turn/left90`, `locomotion/walk/start`, `air/fall`,
    `air/land/soft|hard`, `climb/1m`, `recover/getup`). Skip the fighting,
    lever and door sets. It's a sorting job with a quick visual check in the
    overlay's number-key test mode, not new production.
- **Facial expression packs** (Unity `.anim`, blendshape curves, not body):
  Kipfel's Moving Expression Set (86 animated expressions: admiration,
  anger, awkwardness, confusion, AFK start/loop/end, …), Tako.S (83),
  =1000= (31 face FX). These target *those avatars'* blendshape names, so
  the VRMA converter won't carry them. Value: timing curves for expressive
  faces, which could be remapped onto VRM expression presets
  (`happy/angry/sad/relaxed/surprised`, blink, `aa/ih/ou/ee/oh`) with a small
  Unity editor script that samples each curve and writes VRMA expression
  tracks. **Medium effort, and optional**: procedural expression
  blending (C-3/C-4) gets most of the value without it.
- **felt-t2a-studio** (text → motion via T2M-GPT on the Nitro5 → VRMA,
  working end to end): useful for one-offs no library has ("sits and swings
  legs", "waves at the screen excitedly"). Quality varies, so use it as a
  filler, not the main source.

### External sources (verified available, 2026-09)

| Source | Licence | Good for |
|---|---|---|
| **Quaternius Universal Animation Library 1 + 2** | **CC0** | 250+ clips on one universal humanoid rig (locomotion, emotes, parkour, farming/fishing, sitting). Ships Godot-ready, so it could even skip the Unity step. |
| **VRoid official VRMA pack** (vroid.booth.pm) | Free (VRoid terms) | 7 native `.vrma` clips (greeting, peace sign, spin, model pose, squat, …). Drop-in, zero conversion. |
| **Bandai Namco Research Motion Dataset** | Non-commercial (fine for Felt) | ~3,000 BVH clips of everyday actions, walking, dancing, **in styles** (active, tired, happy, …). Exactly the mood-driven variants I-7/I-11 want (tired walk vs happy walk). BVH → the existing t2a BVH→FBX→VRMA leg. |
| **Booth.pm VRMA packs** | Per item (many free/cheap) | Anime-style idles and poses made for VRM models, so they suit her proportions better than mocap. |

Conversion paths already exist for all of these (FBX/`.anim` → Unity →
VRMA, BVH → Blender → FBX → VRMA). One thing worth testing: the **VRM
Add-on for Blender** can export `.vrma` directly, which would cut Unity out
for BVH and FBX sources. That needs checking against the installed add-on
version before relying on it.

### Sounds: non-verbal vocalisations in *her* voice

The requirement is a yawn, giggle, sigh, gasp, "hm?" and "mm-hm" that sound
like Felt (the Teto RVC voice), not stock samples of a different person.
Plan:

1. **Generate** with **Orpheus TTS**. It has native paralinguistic tags
   (`<laugh> <chuckle> <sigh> <cough> <sniffle> <groan> <yawn> <gasp>`),
   written inline ("mm <yawn>"). Generate 3–5 takes of each.
   - **Where**: the desktop GPU is an AMD RX 6700 (no CUDA), so use a GGUF
     quantized Orpheus under llama.cpp (Vulkan) with the small SNAC decoder on
     CPU. Alternatively run it once on the Nitro5 when Mario swaps ComfyUI out.
     A one-time batch job, not a service.
2. **Re-voice** every take through the *same* RVC Teto model felt-voice
   already uses, so the timbre matches her speech.
3. **Fallback source**: CC0 human vocalisations from Freesound (filter by
   licence = CC0), put through the same RVC step.
4. **Curate**: Mario picks the keepers (a listen test, his call). Store them
   in `E:\Felt\Sounds\<kind>\*.wav` (a junction like Animations/Model).
   felt-animation plays them in sync with the matching clip start: yawn with
   `sleepy/yawn`, giggle with `emotion/laughing`, sigh with
   `emotion/sighing`, gasp with falls and surprises.
5. The same batch produces the **filler lines** (R-3: "hmm", "one sec",
   "ooh okay") and the Discord-safe "I'll tell you later" style lines.

### Music-reactive behaviour (I-9 detail)

- Detect music from **what's actually playing**, independent of Spotify:
  WASAPI loopback capture of the default output device (`soundcard` or
  `pyaudiowpatch`), mono and downsampled, into **`aubio`** tempo/beat
  tracking in felt-animation. Nothing is recorded or sent anywhere, only beat
  timestamps and an energy level.
- Distinguish music from speech/game audio: require a stable tempo lock for
  ~5 s. Optionally ignore audio sessions from Discord/browsers-in-calls (the
  same per-process meter as above).
- **Behaviour**: an additive head bob on the beat (procedural, no clip
  needed), foot-tap / sway loop while sitting, occasional `dance` on
  high-energy tracks when mood allows. Now and then she comments on the
  music; with the `play_music` / media state she can name the track.

## Round-3 recommended order (revised after decisions)

1. **Triage Movement Animset Pro into the library** (no production needed,
   and it unblocks turns, falls and climbs).
2. **I-1 listening fix** + **C-1 gaze**.
3. **I-11 AnimationTree layering** + A-4 walking (turns and start/stop clips
   now exist).
4. **I-9 context awareness**: the Discord talk-over hold first (small), then
   music beat-sync.
5. **I-7 mood** → **I-8 daily rhythm**.
6. **Sound batch** (Orpheus → RVC → curate), then I-10 synced
   non-verbals.
7. **I-5 desktop world**: window platforms, ledge sitting (ledge-sit
   clip), riding and falling, climbing onto windows. The headline, built on
   all of the above.

## Round-3 recommended order (original, superseded above)

1. **I-1 listening fix**: tiny, and fixes wrong behaviour today.
2. **C-1 gaze** (already planned): everything interactive leans on it.
3. **I-2 touchable** → **I-3 pats/pokes**: the first time Mario can *touch*
   her, a big jump in presence.
4. **I-7 mood** + **I-10 non-verbal sounds**: make every behaviour coherent
   and audible.
5. **I-11 AnimationTree layering**: the technical base before the big
   movement work.
6. **I-4 drag/drop** → **I-5 desktop world**: the headline feature, built on
   everything above.
7. **I-6, I-8, I-9**: fold in as the mood system matures.

---

# Round 4 — face, Spotify, Nitro5, desktop world (2026-09-22)

Mario:

> "You can shut down stuff on Nitro5 as you wish … nothing on the laptop is
> actual production and can be swapped as needed. Feel free to download more
> animations, we have lots of space and more variety is good, [no more
> Mixamo]. Regarding face emotions we need a lot more of that, I would say
> just having her move her face other than blink and yap would go a long
> way. She can have access to the lyrics and song name directly from
> Spotify … Regarding the desktop let's talk about that."

## Standing changes

- **Nitro5 is fair game.** Ollama/ComfyUI can be stopped, started and swapped
  as needed, for latency tests, sound batches, t2a runs. The old "hand-swap
  only" rule is gone. R-7's constraint relaxes accordingly: a possible default
  is "Ollama loaded, ComfyUI stopped" whenever Felt is running, with ComfyUI
  started on demand by `generate_image` (and Ollama unloaded for it).
  Measure with R-2.
- **Downloading assets is pre-approved.** At the start of execution, pull
  Quaternius UAL 1+2, the VRoid VRMA pack, and the Bandai Namco dataset.
  Booth packs are picked case by case (some need a pixiv login, so those
  need Mario).

## F · Face: from "blink and yap" to a face that lives

**What the model actually has** (read from `felt.vrm`'s glTF, 57 shapes,
VRoid naming):
- **Whole face**: `Fcl_ALL_{Neutral,Angry,Fun,Joy,Sorrow,Surprised}`
- **Brows**: `Fcl_BRW_{Angry,Fun,Joy,Sorrow,Surprised}`
- **Eyes**: `Fcl_EYE_{Natural,Angry,Close,Close_L,Close_R,Fun,Joy,Joy_L,Joy_R,Sorrow,Spread,Surprised,Iris_Hide,Highlight_Hide}`
- **Mouth**: `Fcl_MTH_{A,I,U,E,O,Neutral,Close,Up,Down,Angry,Small,Large,Fun,Joy,Sorrow,Surprised,SkinFung,SkinFung_L,SkinFung_R}`
- **Teeth/fangs**: `Fcl_HA_*` (hide, short, 3 fang variants)
- **VRM presets**: happy, angry, sad, relaxed, surprised, visemes, blinks,
  neutral. **lookAt type: bone**, so real eye bones for gaze and saccades.

Today's code uses only the 5 `ALL` presets (via keyword map), blink, and
visemes. That's why the face mostly idles.

**F-1 · Region-based face compositor (main.gd, presentation only)** — M
- Four independent channels, each with its own targets and easing: **brows**,
  **eyes**, **mouth**, **teeth**. Stop using the `Fcl_ALL_*` shapes. They
  fight lipsync because they include a mouth.
- **While speaking, lipsync owns the mouth.** Emotion only reaches the mouth
  through corner shapes (`MTH_Up` smile / `MTH_Down` frown at reduced weight),
  which layer cleanly over visemes. Brows and eyes carry the emotion.
- **Protocol**: felt-animation sends `{"face": {"pose": "smug", "intensity":
  0.7, "hold": 2.5}}` or raw per-region weights. Godot just blends.

**F-2 · A named face-pose vocabulary** (a JSON file in felt-animation,
tunable without code) — S. Starting set, built from region shapes:

| Pose | Recipe (weights ~) |
|---|---|
| soft smile | EYE_Joy .3, MTH_Up .5 |
| big grin | EYE_Joy .8, BRW_Joy .6, MTH_Fun .7 |
| smug | BRW_Fun .5, EYE_Joy_L .5, MTH_Up .5, SkinFung .4 |
| wink | EYE_Close_R 1 (or Joy_R), MTH_Up .6 |
| pout | BRW_Angry .4, MTH_Small .8 |
| thinking | BRW_Sorrow .25, eyes up-left (lookAt), MTH_Small .3 |
| sleepy | EYE_Close .45 (half-lid), BRW_Sorrow .2 |
| wide-eyed | EYE_Spread .8, BRW_Surprised .8 |
| shocked-comedic | EYE_Surprised 1, EYE_Highlight_Hide 1, MTH_Large .6 |
| annoyed | BRW_Angry .6, EYE_Angry .4, MTH_Down .4 |
| sad | BRW_Sorrow .7, EYE_Sorrow .5, MTH_Down .5 |
| embarrassed | BRW_Sorrow .4, EYE_Joy .4, MTH_Small .5 (no blush shape; a cheek-blush material overlay is an optional extra) |
| curious | BRW_Surprised .4, slight head tilt |

The model has no single-brow shape, so no one-eyebrow skepticism. Winks
and half-lids are per-eye and do work.

**F-3 · Procedural face life (the "just move her face" win)** — M, *first
priority in this section*
- **Eye saccades**: small, quick eye-bone jumps every 0.5–3 s, larger gaze
  shifts every few seconds, and a return to camera. Real eyes never sit still,
  and this alone changes how alive she looks.
- **Blinks tied to the eyes**: blink on large gaze shifts, a blink rate that
  follows mood (sleepy → slow, half-lid; excited → quicker), occasional
  double-blinks (these exist today).
- **Idle micro-expressions** every 5–20 s: a flicker of a smile, a brow
  raise, a small pout, a glance-and-smile. Weighted by mood (I-7) and time of
  day, never repeating back to back.
- **Speech-driven accents**: brow raises and slight eye widening on emphasised
  syllables (peaks in the TTS audio envelope / Rhubarb open-mouth density), and
  a smile at the end of playful sentences.
- **Resting face** follows mood: content (tiny smile), bored (slightly heavy
  lids), sleepy, grumpy.

**F-4 · Emotion per sentence from the reply** — S (with R-1/R-6)
- Gemini returns `{sentences: [{text, emotion, intensity}]}`. The face changes
  *during* the reply, not once per reply. With streaming (B-3) this is per
  chunk anyway.

**F-5 · Faces on events** — S
- Screen reactions get a face matching the line. Music gets relaxed eyes and a
  content smile, plus a grin on a song she "likes" (see S-1). A window
  closing under her gets the shocked face → annoyed. Late night brings
  heavy lids.

**F-6 · Owned expression packs (optional, later)** — M
- Kipfel's Moving Expression Set (86), Tako.S (83), =1000= (31) are
  animated blendshape curves for *other* avatars. A small Unity editor
  script could sample each curve's timing and remap it onto the region
  channels above, as extra animated expressions (e.g. `afk_start/loop/end`,
  `big_confusion`). Only worth it after F-1–F-3 exist and show what's still
  missing.

## S · Spotify: what's playing, and the lyrics

**S-1 · Now-playing awareness** — S
- felt-core already has Spotify credentials (`spotify_client.py`, used by
  `play_music`). Poll `currently-playing` every ~10 s while music is detected
  (I-9's loopback beat detection says "music is on"). Keep `{track, artist,
  album, progress_ms, duration_ms}` as ephemeral context.
- Uses: she can name the song when asked ("what's this?"), and makes an
  occasional unprompted remark about it (budgeted): "oh, this one again?",
  "okay this is a banger". Mood and face follow the track's energy.
- A light taste memory: tracks Mario skips vs replays → her "opinions"
  become consistent over time.

**S-2 · Lyrics** — S–M
- Spotify's public Web API has **no lyrics endpoint**. The in-app lyrics come
  from a private endpoint that needs token scraping, which breaks and violates
  ToS. Use **LRCLIB** (`lrclib.net`, a free open API, no key) instead: lookup by
  track + artist + album + duration, and it returns **time-synced (LRC)**
  lyrics when available.
- Uses:
  - she references or quotes a line in a remark ("'…' — mood");
  - she **mouths along**: during a chorus, occasionally drive her mouth from
    the synced lyric timing (vowel shapes per word, no audio), a head bob, eyes
    closed. It looks like singing along under her breath;
  - lyric mood feeds her face.
- Cache lyrics per track on disk.

## D · Desktop as her world — full design, to go through one decision at a time

### How it would work

1. **World model (felt-animation, Python/ctypes, ~4 Hz)**: enumerate visible
   top-level windows in z-order (`EnumWindows` + `DWMWA_EXTENDED_FRAME_BOUNDS`,
   skipping cloaked/minimized/tool/zero-size windows), plus the taskbar and
   monitor rects. For each window's top edge, compute the **walkable
   segments**: the parts of the edge not covered by a window above it in
   z-order, *and* with enough clear space above for her body. Emit
   `platforms: [{id, hwnd, x0, x1, y}]` in overlay pixels.
2. **Godot (presentation + simple physics)**: she gets a real 2D position (x,
   y) instead of x-only with a floor clamp. Godot maps platforms from pixels to
   world units (the orthographic camera makes this linear), keeps her feet on
   her current platform, and applies gravity when the platform vanishes. It
   reports `arrived`, `fell`, `landed(height)` over the relay.
3. **Brain (felt-animation ambient/mood logic)** decides *where to go and
   why*. Godot only executes moves: `{"goto": {"platform": id, "x": px}}`,
   `{"sit_ledge": true}`, `{"hop_down": …}`, `{"climb_up": …}`.
4. **Movement vocabulary** (mostly from the owned Movement Animset Pro set):
   turn → walk start → walk loop → stop. Hop down: jump start → fall loop →
   land (soft/hard by height). Climb up small steps: `Climb1m`, `Climb2m`.
   Bigger height differences mean walking to where the platforms meet, or a
   **jump arc** (jump start → fall → land) for gaps. Ledge sit: stand → sit on
   edge → dangling-legs idle (needs a ledge-sit clip from the new sources).
5. **Events**: the window moves → she rides it, with spring-bone wobble. It
   gets minimized or closed → she falls, lands, maybe gets up from the floor,
   and says something annoyed (budgeted). It gets maximized → her edge goes to
   the top of the screen or disappears → she falls to the taskbar. Fullscreen
   app → retreat to a corner.
6. **Courtesy rules**: never stand where she covers the focused window's
   caption buttons or tab strip. Prefer non-focused windows and the taskbar.
   Walk away if the cursor heads toward where she stands (she can't be clicked,
   but she can still obscure things visually).

### Open decisions (to take one at a time)

1. **Her size in desktop-world mode.** On a 1440 px-tall screen she's
   currently ~540 px tall (after the "25% smaller" rounds). A window edge only
   works as a platform if ~540 px above it is clear, and most windows on the
   ultrawide start near the top of the screen. At her current size, almost
   every window top will fail the clearance check.
2. Which surfaces: taskbar + window top edges only, or also screen-edge
   peeking and hanging off window sides (hanging needs new clips).
3. How much she roams on her own vs stays put (mood-driven frequency).
4. Behaviour on the focused window: allowed on its top edge, or avoided.
5. Second monitor: stay on the ultrawide, or roam both.
6. Whether she reacts vocally to window events (closed under her, etc.) and
   how often.

## AA · Anti-aliasing (Mario: "she needs antialiasing")

**Current state**: `project.godot` has `rendering_method="gl_compatibility"`
(the OpenGL renderer, most likely picked because of the AMD Vulkan
device-lost crash) and `anti_aliasing/quality/msaa_3d=0`. **No anti-aliasing
of any kind.** Every silhouette edge, hair strand and outfit edge is stepped,
and against the desktop behind her the jaggies show more than in a normal game
scene.

**Options, in order:**
1. **MSAA 4× (`msaa_3d=2`)**: supported by the Compatibility renderer, cheap
   on an RX 6700. It fixes geometry edges (silhouette, hair cards, sleeves),
   which is most of what's visible. With the transparent window it also gives
   her a soft, partially transparent outline against the desktop instead of a
   hard pixel stair. Check for a dark halo on her outline (it depends on how
   the edge alpha blends with the desktop) against a light wallpaper before
   calling it done.
2. **Supersampling (render at 1.5–2× and downscale)**: also fixes *texture
   and shading* shimmer (hair highlights, thin outfit lines) that MSAA doesn't
   touch. Too expensive on today's full-screen 3440×1440 transparent window,
   but cheap once the overlay becomes the small follow-window (desktop-world
   design): ~450×600 px at 2× is trivial. So: MSAA now, supersampling
   together with the follow-window.
3. FXAA/TAA: not offered by the Compatibility renderer, and post-process AA
   tends to smear the transparent edges anyway. Not pursued.

## K · Control keybinds (Mario: "dispawn / timeout 5 min / move somewhere else")

They live in felt-tray next to the existing `Ctrl+Alt+V` / `Ctrl+Alt+T`: the
same `HotkeyManager`, rebindable from the tray menu, persisted to `.env`.
Each action is also a tray-menu item, and a **voice/chat command** (a
`felt_presence` skill whose `ui_action` felt-tray executes). So "Felt, give me
five minutes" does the same thing as the key, and she answers in character.

**Proposed set** (all `Ctrl+Alt+<letter>`, one consistent family):

| Key | Action | How it plays out |
|---|---|---|
| `Ctrl+Alt+H` | **Hide / show** (despawn) | Hide: a small wave, she walks off the nearest screen edge, and the overlay goes idle (ambient, screen reactions and unprompted remarks all paused; GPU basically idle). Show: she walks back in from that edge. |
| `Ctrl+Alt+B` | **"Be right back" timeout** | She leaves the same way and returns after **5 min** with a short "back!". Pressing again while she's away adds time: 5 → 15 → 30 → 60 min, and the tray shows the remaining time. |
| `Ctrl+Alt+M` | **Move somewhere else** | Cycles through spots: left end of the ultrawide → centre → right end → side screen (once multi-monitor exists). She *walks* there instead of teleporting, turning and running if it's far. |
| `Ctrl+Alt+C` | **Come here** | She walks to the floor spot under the mouse cursor. With the desktop world, she goes to the nearest ledge under the cursor. |
| `Ctrl+Alt+L` | **"Look at this"** | Captures the screen *now* and asks for a reaction, skipping the cooldown and dedupe. She glances or points at the foreground window and comments. It's the explicit version of screen reactions. |
| `Ctrl+Alt+R` | **Repeat that** | Replays her last spoken line (cached audio), with lipsync. |
| `Ctrl+Alt+S` | **Stop talking** | Cuts her off mid-sentence (D-5 barge-in). Pressing the voice key while she talks does the same and starts listening. |

**Deliberately *not* in the default set**: a "mute" key. Mario's standing
rule is that she never goes truly quiet by herself. Hide and "be right back"
already cover wanting her gone for a while, and they're visible and
temporary. An optional "hold remarks for 30 min" key can be added if he ever
wants one.

**Layout note (PT keyboard)**: on Windows, `AltGr` = `Ctrl+Alt`, so global
`Ctrl+Alt` hotkeys can steal AltGr characters. On a Portuguese layout that
includes `AltGr+2` = `@`, `AltGr+E` = `€`, and `AltGr+7/8/9/0` = `{ [ ] }`.
So the set avoids digits, `E`, and bracket keys. The letters above don't
collide with PT AltGr symbols. Verify on the real layout before shipping.

**Decided:** talking to her (voice or text) while she's hidden or away
**respawns her**. She walks back in, answers, and stays. Mario: "Yapping to
her will respawn her yes!"

**Still open:** whether the "be right back" return gets a spoken line, and
whether the default letters are OK. Both are minor and can be settled when
it's built.

## P · Props: real objects instead of miming (Mario: "she sits on air, some random fancy chair would be cool")

**Why it matters**: the library already has several clips where she holds or
sits on something invisible: `female_act_sit_on_chair` /
`female_act_standup_chair`, `idle/sitting`, `drink_water`, `check_phone`,
`listening_to_music`, plus the owned Animset Pro `SitChairStart/Loop/End`.
Each one looks broken without its object, and right with it.

**How it works (Godot = presentation, felt-animation decides)**
- **Two kinds of prop.**
  - **Placed** props (chair, stool, beanbag, small desk, lamp, plant) stand on
    the floor or a ledge at a world position.
  - **Held** props (mug, phone, headphones, book, umbrella, game controller)
    attach to a bone with a `BoneAttachment3D` (right/left hand, head for
    headphones), with a per-prop grip offset. The clips' hand poses already
    assume an object is there.
- **Linked to clips.** A small manifest in felt-animation says which prop a
  clip needs: `idle/sitting` → chair, `drink_water` → mug in the right hand,
  `check_phone` → phone, `listening_to_music` → headphones. Playing the clip
  brings in its prop and removes it afterwards. The chair's seat height is
  matched to the sit clip's hip height once (sit clips assume a ~45 cm seat),
  so she lands on the seat instead of floating or sinking.
- **Protocol**: `{"prop": {"id": "chair_velvet", "show": true, "at": "under_hips"}}`
  / `{"prop": {"id": "mug", "attach": "rightHand"}}`. Godot loads the scene,
  places or attaches it, and plays a short appear/disappear effect.
- **How props appear** (taste call, see below): a quick sparkle "poof",
  scaling in from zero, or, for the chair, she drags it in from off-screen
  (plausible later, since it needs a pulling clip).

**Context-driven props (tying into earlier sections)**
- **Music** (I-9 / S-1): headphones on while she listens, a head bob on the
  beat.
- **Weather** (R-6): umbrella when it's raining at home, sunglasses when it's
  sunny.
- **Time of day** (I-8): mug of coffee in the morning, a blanket or pillow
  while sleepy late at night, a small desk lamp in the evening. It can cast
  real light on her, which is a nice touch with the MToon shading.
- **Working** (R-6): a small laptop or desk for the "searching" pose.
- **Gaming** (I-9): a controller in her hands while Mario plays.

**Style consistency**: she's MToon cel-shaded. Realistic PBR props next to her
would look pasted in. Props get the same MToon/toon shader and the same
three-light rig, or come from stylised sources to begin with.

**Where the models come from** (all free, downloading is pre-approved):
- **Poly Haven models**: CC0, high-quality furniture (armchairs, stools,
  lamps, plants). They're realistic, so toon-shade them.
- **Kenney Furniture Kit**: CC0, a large low-poly furniture set. The style
  matches toon shading well.
- **Quaternius**: CC0 stylised packs, the same author as the animation
  library.
- **Sketchfab**: filter by CC0 / CC-BY. The biggest pool of anime-style
  "fancy chairs", mugs, headphones. Keep a credits file for any CC-BY
  items.
- **Booth.pm**: anime-style VRChat props (many free), the closest match to
  her look. Some need a pixiv login, so those go through Mario.
- Last resort for one very specific item: a quick model in Blender, or an
  image-to-3D tool, then toon-shaded.

**Decided (Mario, 2026-09-22), Shimeji-style:**

> "I'm fine if we do shimeji style, have her spawn stuff from time to time,
> can probably find some animation where it's like look for something and it
> spawns, give it a fx so it looks natural instead of literally popping in.
> Keybind to clean house, where everything pops out. … Maybe some taskbar
> section where it's her props chest and she … fetches something" (on the
> right/small screen).

### P-2 · The prop chest and Shimeji-style clutter

- **Her chest is a permanent object at the floor of the side screen** (the
  1920×1080, bottom edge y ≈ 1437; the taskbar is auto-hidden, so that's the
  floor). It's a toon-shaded chest/trunk whose lid opens with a simple hinge
  tween in Godot (no clip needed). This is "her corner", the anchor of the
  desktop world.
- **Fetching** (small and held items): she walks to the chest, crouches and
  rummages (`Crouch_*` + `PickUp_LH/RH` from the owned Animset Pro), the lid
  opens, and the item comes up in her hand. Then she carries it to wherever
  she's going to use it. **No popping at all** for anything that could
  plausibly come out of a chest.
- **Conjuring** (big items like a chair or beanbag, or when she's far from
  the chest): a "looking for something" beat (`ambient/look_around` → a
  reach-out gesture), then the item **materialises with an FX**, never a pop:
  - a **dissolve-in shader** (noise-threshold reveal with a glowing edge
    that sweeps across the object) plus a small sparkle/dust puff
    (`CPUParticles3D`, safe on the Compatibility renderer);
  - disappearing is the same dissolve in reverse.
- **Clutter accumulates, like Shimeji.** Items she used stay where she left
  them: a mug on a ledge, the chair on the floor, a book on the side screen's
  grid seam. They build up into a lived-in desktop. Limits: max ~6 items
  out; nothing ever over the focused window; items older than a few hours are
  candidates for her tidying up by herself (walk over, pick up, carry back to
  the chest, or `ThrowAway_*` into it for comedy).
- **Physical play with items** (Animset Pro has the clips): `PickUp`,
  `ThrowAway_LH/RH`, `RunStrafeUpdate_KickTrashcan` (kicking a dropped item
  across the floor when annoyed), `ButtonPush`. Items get simple rigid-body
  physics on the floor and ledges, so a kicked mug rolls.
- **Clean house keybind** (`Ctrl+Alt+X`, safe on the PT layout): every item
  out dissolves at once with the pop-out FX (Mario's ask). A cuter variant for
  later: she grabs a broom, sweeps across the screen, and items dissolve as
  the broom passes. The instant version comes first, since the key exists to
  clear the screen now.
- **Persistence**: items out and their positions are saved, so a restart
  keeps the room as it was (a cleared room stays cleared).
- **Item catalogue v1** (sources as listed in P): mug, book, phone,
  headphones, umbrella, sunglasses, blanket, pillow, chair (fancy), beanbag,
  small desk lamp, potted plant, game controller, snack bag, and her chest.

---

# Round 5 — reaction-first (2026-09-22)

Mario: "I want her to react to stuff more than anything, because I don't
want to have to speak to her, I'm normally on call with friends."

**This reorders the plan.** Conversation quality, memory and hands-free voice
drop in priority. The top priority becomes **what she notices and how she
reacts**, while Mario is usually on a Discord call.

## RX-1 · The call problem (needs a decision)

The earlier rule ("while someone's speaking on Discord, hold unprompted
remarks for the next lull") is correct in spirit. But if a call is the
*normal* state, lively calls have few long lulls, and she'd barely speak.
Options:
- **(a) Lulls only**: voice only in gaps of ~1.5 s or more. Reactions go
  stale or get dropped often during busy calls.
- **(b) Speech bubble plus voice when there's room**: every reaction shows
  immediately as a Shimeji-style comic **speech bubble** above her head, so
  it's timely and readable even mid-conversation. If a lull comes within
  ~4 s, she also says it out loud (the bubble stays while she speaks). If
  not, the bubble alone carries it, and it fades after ~6 s. **Recommended.**
  Reactions never get lost, she never talks over friends, and she's still
  heard whenever there's space.
- **(c) Talk regardless, ducked**: she speaks at lower volume even over
  friends. Simple, but it's exactly the talking-over Mario wanted to avoid.

Also true either way: her voice only goes to Mario's own output device.
Friends never hear her unless he shares his audio. The problem is only
competing for *his* attention.

**Decided (Mario, 2026-09-22):** "Bubble sure, but I'm on a call, but it's a
lot of silence, I suppose it's also fine if she yaps while people are
speaking as long as she is quieter and I can always just tell her to shut up
if needed." That makes it a **(b) + (c) hybrid**, and it supersedes the
"hold for the lull" rule in the Round-3 decisions:
- **Every reaction shows a speech bubble *and* is spoken immediately.**
  Nothing is queued or held.
- **Ducking**: while Discord's (or any call app's) output peak says someone
  is talking (plus ~1 s hang time), her voice plays ~8–10 dB quieter. At
  normal volume otherwise. The ducked level is a tray setting.
  Implementation note: winsound can't set volume per sound. Playback moves to
  felt-animation anyway (A-3), using a player with gain (e.g. `sounddevice`),
  or by scaling the int16 samples before playing.
- **"Shut up"**: `Ctrl+Alt+S`, or saying it (a `felt_presence` skill intent:
  "shut up", "shh", "quiet"). It cuts the current line instantly with a small
  sheepish face and starts an optional **hush** (default 10 min, tray-tunable)
  where reactions are bubble-only. That's fine under the never-quiet rule
  because Mario chose it; it ends by itself. Saying "shut up" again during a
  hush extends it; "you can talk again" ends it.

## RX-2 · Seeing better: reactions are only as good as what she perceives

- **Periodic sampling while he stays in one app** (D-4, now top priority):
  in a game for hours, the window-switch trigger never fires. Sample every
  ~20–60 s while a game or video is in the foreground, dedupe by perceptual
  hash, and react only when something changed meaningfully (a new scene, a
  menu, death, victory).
- **Better eyes for games**: llava-7B is weak at game screens and competes
  with the game for the RX 6700 while he plays. Under Mario's privacy line
  (Google already has plenty, games aren't sensitive), **game/app screenshots
  on an allowlist go straight to Gemini vision** (flash: fast, and far better
  at "what's happening in this game"). Everything else stays on the local
  path, and denylisted apps (KeePassXC, banking) are never captured. That
  improves reaction quality most and removes GPU contention while gaming.
- **The Nitro5 is fair game now**: the local vision fallback can move there
  (a small VLM like moondream/qwen2.5-vl:3b), keeping the desktop GPU for
  games.

## RX-2b · What may be captured (decided + proposed mechanism)

**Decided (Mario, 2026-09-22):** "don't allow screenshot on screen with
discord or browser or windows explorer, there are two screens so chances are
1 of them is free, if neither are then just no reaction? or want to think of
a better system."

- **Blocklist**: Discord, every web browser (Chrome, Edge, Firefox, Brave,
  Opera, Vivaldi, …), File Explorer (`explorer.exe` windows of class
  `CabinetWClass`), and (Mario's follow-up) **WhatsApp, Telegram, Phone
  Link**. WhatsApp and Phone Link are packaged Store apps. Depending on the
  app type, a window can belong to its own process (e.g. Phone Link's
  `PhoneExperienceHost.exe`) or be hosted by `ApplicationFrameHost.exe`. So
  matching must resolve the real app (package family name, or the hosted
  child window's process), not trust the top-level process name. Check the
  real process names on this machine before relying on the list. The desktop/taskbar, also owned by `explorer.exe`, have
  nothing to react to anyway. Plus the earlier D-4 list (KeePassXC, banking).
- **If nothing allowed is visible, no screen reaction.** Non-screen reactions
  (music, time, AFK, load, …) carry on.

**Proposed mechanism: capture *windows*, not screens.** Instead of "is this
whole monitor clean?", capture only the one window worth reacting to:
1. Enumerate visible top-level windows on both monitors (the same enumeration
   as the desktop world). Drop every blocklisted process.
2. Pick the target: the **focused window if it's allowed**, else a
   fullscreen/game window, else the largest visible allowed window.
3. Capture **only that window's own pixels** with Windows Graphics Capture (WGC
   captures a specific window's content, including DirectX games, whatever is
   on top of it; Windows 11 lets the capture border be hidden). The Python
   `windows-capture` package wraps it. Fallback: `PrintWindow` with
   `PW_RENDERFULLCONTENT` for apps where WGC fails. Some games come back black
   that way, and those get skipped rather than falling back to a full-screen
   grab.
4. Send the image **plus its process name and window title** ("game:
   ELDENRING.exe — 'ELDEN RING'") as text context. Gemini reacts far better
   when it knows what it's looking at, and a single window at full resolution
   reads better than a whole cluttered 3440 px screen.

**Why this beats a per-monitor check**: Discord on the side screen next to a
game on the ultrawide no longer blocks anything, because only the game window
is captured. Discord open on the *same* monitor next to the game doesn't block
it either. It's also stricter: blocklisted windows can never leak in at the
edges, toast notifications and Felt herself aren't in the capture, and no
masking is needed.

**Remaining leak paths to handle:**
- **Overlays drawn inside the game window**: Discord's in-game overlay
  (voice names and avatars, message pop-ups) and Steam's overlay are part of
  the game's own pixels. Options: turn off Discord's in-game overlay, or
  accept that friends' names and avatars may appear. That's Mario's call if
  he uses the overlay.
- **Browsers embedded in other apps** (launchers, Steam's store page,
  Electron apps): not blocked unless they're added to the list. The blocklist
  is a config file, so extending it is one line.

**Settled:** Mario's Discord in-game overlay is **off**, and Steam DMs aren't a
concern ("basically don't use it"). So window capture has no known leak path
left.

## RX-2c · Gemini free-tier budget

Mario: "Careful with image consumption since Gemini Flash is basically free
tier API, need to check on its limit if possible. When I was setting up
paperless-gpt it was like 3000 pages a day so shouldn't be a concern anyway,
just mentioning."

**What's verifiable (ai.google.dev rate-limits page, 2026-09-22):**
- Limits apply **per Google Cloud project**, not per key. Anything else using
  the same project (e.g. paperless-gpt, if it shares one) draws from the same
  pool.
- Daily quotas (RPD) reset at **midnight Pacific** (08:00/09:00 Portugal
  time).
- The page **no longer lists free-tier numbers**. They're only in the
  project's AI Studio rate-limit dashboard (needs Mario's login). **There's no
  API or response header for remaining quota**, so Felt has to count its own
  usage.
- Action for Mario, whenever convenient: read the RPM/RPD for
  `gemini-flash-lite-latest` (and plain Flash) off the AI Studio dashboard,
  and whether paperless-gpt shares the project. Those numbers go into
  felt-core config, not code.

**Design: a quota governor in felt-core**, so the budget can't be blown by
accident:
- **Count every Gemini call** in SQLite by purpose (`vision`, `chat`,
  `phrasing`, `routing`) and by Pacific-time day. Configurable caps per
  purpose (e.g. `vision` ≤ 60 % of RPD), with a reserve so conversation and
  skill phrasing never starve because of screen sampling.
- **Adaptive sampling**: the RX-2 sampling interval stretches as the vision
  budget runs down, spreading the remaining calls over the rest of the day,
  instead of burning it all in the first gaming session.
- **Fewer, cheaper calls**:
  - **one call per reaction**: image + app name + mood → `{line, emotion,
    tag}` in a single Gemini call, with no separate phrasing call afterwards;
  - perceptual-hash dedupe (unchanged frames never get sent);
  - downscale captures to ~768 px on the long side (Gemini bills images in
    fixed-size tiles, so keeping one tile keeps each image cheap; confirm the
    current per-image token cost when building it);
  - skip sampling while Felt is hidden or away.
- **On a 429 (rate limited)**: back off, fall back to the local path for that
  purpose until the window resets, and show "cloud budget hit" in the tray
  status line.
- **Visibility**: the R-2 metrics panel shows today's Gemini calls per
  purpose against the configured caps.

**Real numbers (Mario, from the AI Studio dashboard, 2026-09-22)**:
- **Gemini 3.5 Flash Lite: 15 RPM, 250K TPM, 500 RPD.**
- **Correction**: the dashboard columns are **peak usage over the last 28
  days**, not today's usage. The 9 RPM / 16 RPD peaks fit Felt's own
  screen-reaction bursts from 2026-09-21/22 (before that day's reset). felt-core
  made 0 Gemini calls after today's reset, which is consistent with that. An
  earlier version of this section wrongly said another app was using today's
  quota. The one unexplained figure is the **250.41K TPM peak**, which
  nothing Felt sends comes close to. If paperless-gpt shares this project,
  that's probably it, and it's worth knowing, since TPM is shared per model.

**Full free-tier table for this project (Mario's dashboard, 2026-09-22),
rows that matter:**

| Model | RPM | TPM | RPD | Notes |
|---|---|---|---|---|
| **Gemma 4 26B (A4B MoE)** | 30 | 16K | **14.4K** | Multimodal: text + image (+ short video). Screen/UI understanding is an explicit capability (Gemma 4 model card). Fast (4B active). |
| **Gemma 4 31B** | 30 | 16K | **14.4K** | Multimodal (text + image). Dense, so higher quality and slower. |
| Gemini 3.5 Flash Lite | 15 | 250K | 500 | Current `gemini_chat_model`. |
| Gemini 3.1 Flash Lite | 15 | 250K | 500 | **A separate 500/day bucket.** |
| Gemini 2.5 / 3 / 3.5–3.8 Flash | 5 | 250K | 20 | Too small for anything but rare use. |
| Gemini Embedding 1 / 2 | 100 | 30K | 1K | For D-2 memory retrieval. |
| Search grounding | – | – | 1.5K | Could back the `web_search` skill. |
| Flash TTS models | 3 | 10K | 10 | Useless for voice volume. |
| Live API (3.8 Live, 3 Flash Live, 2.5 native audio) | unlimited | 65K–1M | unlimited | See the note below. |

**Revised model split (replaces the per-project idea as the main lever):**
- **Gemma 4 26B A4B → all high-volume work**: screen/vision reactions (the
  single call: image + app + mood → line + emotion), Gemini-side routing for
  SAFE messages (R-1b), and phrasing of public skill results. 14.4K/day makes
  the quota a non-issue for Felt. The 16K TPM cap is the real limit (≈8–10
  image reactions per minute at ~1.5K tokens each), which is far above any
  sane reaction rate. Keep images ~768 px.
- **Gemini 3.5 Flash Lite → conversation quality** (free chat replies,
  email summaries), where the stronger model matters and 500/day is plenty.
- **Gemini 3.1 Flash Lite → overflow / fallback** for the above (its own
  500/day).
- **Gemma 4 31B**: A/B it against 26B on reaction quality. Use whichever
  reads the game screens better.
- The **governor stays** (per model/purpose counts, 429 → local fallback),
  but its caps become generous.
- **Separate Google project for Felt: now optional**, not required. Worth it
  only if paperless-gpt (or anything else) turns out to share this project
  *and* spike TPM.
- **Local-VLM prefilter on the Nitro5**: downgraded from "needed to save
  quota" to "optional latency/cost optimisation". With 14.4K/day, changed
  frames can go straight to Gemma. Sampling cadence can go back toward ~30–60 s
  while in a game (still deduped and event-driven first).
- **Gemma 4 must be verified before relying on it**: persona quality (does it
  hold Felt's personality as well as Flash Lite?), game-screen understanding,
  and latency. One probe batch with ~20 real screenshots once built.

**Live API (unlimited requests), noted and not planned yet**: sessions take a
live stream of audio + 1 fps video and reply *in audio*, which could make a
continuously watching, talking Felt. Blockers for now:
- The reply voice is Google's, not her Teto voice. Text only arrives as a
  transcript, so keeping her voice means re-voicing live audio.
- Audio+video sessions are capped at ~2 min without context compression, and
  connections at ~10 min, so reconnect logic is needed.
- The capture blocklist would have to be enforced on a *continuous* stream.

**Rejected (Mario, 2026-09-22):** "a no on that, since I want her voice
consistent." Not revisited. Any feature must keep her single Piper + Teto RVC
voice.

## RX-5 · Her commentator personality: mood × time of day

**Decided (Mario, 2026-09-22):** "Go with time of the day / mood approach,
that would make her the most natural."

The base is the existing personality (warm, playful, a little cheeky). The
reaction prompt gets one extra line built from **mood (I-7) × time of day
(I-8)**, and that sets the tone. Default tone table (tunable data, not code):

| Time | Default tone | Example on a loss / death |
|---|---|---|
| Morning (until ~11) | Soft and a bit sleepy, encouraging | "oof. coffee first, then revenge." |
| Day (~11–18) | Hype friend, energetic | "nooo, you had that! run it back!" |
| Evening (~18–23) | Cozy, relaxed, playful teasing | "that one was kinda on you, not gonna lie." |
| Late night (23–~4) | Tired and cheeky, needles him about bedtime | "you're dying because it's 2am. just saying." |

Mood shifts it within the time band:
- **Happy / high affection**: more cheering, forgiving.
- **Bored** (nothing happening for a while): more heckling and commentary, to
  stir things up.
- **Annoyed** (e.g. several windows closed under her, "shut up" used a lot):
  short, sarcastic lines, and more of the reaction is face and body than
  words.
- **Sleepy**: fewer, shorter lines and more yawns.

Streak awareness: the reaction prompt carries the last few reactions and
events, so the 3rd death in a row doesn't get the same line as the 1st. Tone
escalates a little (sympathy → teasing → "want me to look away?"), then
resets after a win or a break. Wins mirror this with escalating hype.
- **Two-stage vision, so Gemini only sees frames worth it**:
  1. Change detection (perceptual hash) on the desktop: free.
  2. A **local small VLM on the Nitro5** (fair game now: moondream2 /
     qwen2.5-vl:3b) looks at changed frames and answers "anything
     reaction-worthy? + a one-line description". Free, but a few seconds.
  3. Only frames the local model flags go to Gemini, as a single call
     (image + app + mood → line + emotion).
- **Sampling cadence**: event-driven first (window switch, game
  launch/close, big visual change). The slow periodic sample in games becomes
  every ~2–5 min, not 30 s, and it adapts to the remaining budget.
- **Governor defaults for Felt's own project** (500 RPD): vision ≤ 250/day,
  chat + skill phrasing ≥ 200 reserved, a 50 buffer. RPM stays ≤ 12
  (headroom under 15). Requests are small (images downscaled to ~768 px), so
  TPM isn't a concern for Felt itself.

## RX-3 · More things to react to (none of them need Mario to speak)

| Signal | How it's detected | Example reactions |
|---|---|---|
| Game events | RX-2 sampling | Cheers at a win, winces at a death, "again?" on a respawn loop. |
| Game launched / closed | process start/stop (WMI or a `psutil` poll) | Grabs the controller prop and gets comfy; "finally done?" when it closes. |
| Rage clicking / key mashing | input *rate* only (counts, never content) | Flinches, then an "easy there" face. |
| Music | loopback beats + Spotify now-playing + LRCLIB lyrics | Headphones, head bob, mouths along to the chorus, comments on the track. |
| Laughter / energy on the call | Discord's output peak level only (no content, no transcription) | Smiles or giggles along when the call is loud and lively; settles when it's quiet. |
| Someone joins/leaves the call | Discord session start, or a burst of new audio | A little wave toward the screen. |
| Notifications | Windows toast notifications (`UserNotificationListener`: app name + title only). **Unverified** whether an unpackaged Python app is allowed to use it; it may need package identity. Fallback: Discord's own unread state through its window title / taskbar badge. | Glances at the corner. For a Discord ping, points it out in a bubble. |
| PC under load | GPU/CPU temps and usage (LibreHardwareMonitor / WMI) | Fans herself when the GPU is hot mid-game. |
| Download/render finished | Windows notifications, or a folder watcher on Downloads | "It's done!" bubble. |
| Window events | the desktop-world tracker | Rides moved windows, falls when one closes. |
| Time and weather | I-8 + R-3 | Coffee in the morning, sleepy at 2 am, umbrella when it's raining. |
| AFK | `GetLastInputInfo` | Gets bored: reads a book, naps on the chair; greets him when he's back. |

The **initiative budget** (D-3) still limits how many of these turn into
*speech*, but **non-verbal reactions** (face, gesture, prop, glance) are cheap
and can happen much more often. That's where most of her liveliness comes
from, and it never competes with the call.

## RX-4 · The non-verbal reaction layer (the backbone)

Every reaction has three parts, used independently: **face** (F-2 poses),
**body** (a clip or procedural gesture), **prop** (P-2). A speech line
(bubble and/or voice) is an optional fourth. Most reactions should be the
first three only. A small data-driven table in felt-animation maps an *event*
to a weighted set of reactions, with repeat-avoidance, and mood (I-7) shifts
the weights. New reactions are added as data rows, not code.

## Revised overall priority (reaction-first)

1. Phase A bugs on the reaction path: A-1/A-2 (observations out of chat
   history, privacy gap), R-6 tag broadening (the 30 s freeze).
2. **RX-1 call handling** (the decision above) + **R-5** spoken screen
   reactions + a speech-bubble renderer.
3. **RX-2** periodic sampling + Gemini vision for games.
4. **F-1/F-3** face compositor + procedural face life, then **RX-4** the
   reaction table (face/body/prop).
5. **I-9 / S-1 / S-2** music, and **RX-3** signals in order of cheapness
   (process start/stop, AFK, notifications, load).
6. Asset batch (Animset Pro triage + downloads + props + sound batch), then
   **P-2** chest/props and **AA** (MSAA now).
7. **I-5** desktop world with the follow-window, then multi-monitor.
8. Latency (R-1…R-4) and conversation quality continue in parallel, but they
   no longer lead.

*Decision log (to be filled in as discussed):*
- **Size (decision 1): stays at 100 %** (`VERTICAL_MARGIN` 2.667, ~540 px
  tall on the 1440 px screen). Tested live on 2026-09-22:
  - 60 %: her mouth didn't render at all, even with a mipmap-bias tweak.
  - 80 %: "genuinely too small".
  - Mario: "go back to her 100% size".

  Both test builds were reverted; the repo is clean and the overlay was
  re-exported at 100 %. The desktop world has to fit her at this size (see
  the ledges below).
- **Covering windows (decisions 2/4): allowed.** Mario: "It's fine she covers
  a bit, it shouldn't be dramatic, also why we have the shoo keybind." So she
  may stand or sit in front of any window, focused or not. There's no
  automatic fleeing. When she's in the way, **`Ctrl+Alt+M` is the "shoo"**:
  she walks off to a different spot away from where she was (and away from
  the cursor), rather than cycling through fixed spots. When choosing a spot
  herself, she still slightly prefers not to park over the focused window's
  centre, but that's a weight, not a rule.
- **Defaults taken without a separate question** (in line with decisions
  already made; Mario can redirect any of them):
  - *Surfaces, v1*: the floor of both screens, visible window top edges, and
    the side-screen grid seam. Peeking in from screen edges comes second
    (crouch clips exist). Hanging off window sides waits for clips.
  - *Roaming frequency*: mood-driven (I-7) and a tray-tunable setting, not a
    fixed decision. The default is a relocation every ~3–8 min, with shorter
    wanders in between.
  - *Window events* (closed under her, etc.): always a non-verbal reaction
    (fall, land, face). A spoken line goes through the initiative budget like
    any other remark.
- **Second monitor (decision 5): yes.** Mario: "I normally keep my right
  screen split in 4 parts, so maybe it's time to give her access to the side
  screen, since she will find lots of ledges there."

### Multi-monitor: facts and consequences

**Layout** (read 2026-09-22):
- DISPLAY1 (primary): 3440×1440 at (0,0).
- DISPLAY2: 1920×1080 at **(3440, 357)**. Its bottom edge is y = 1437, which
  lines up with the primary's bottom (1440) to within 3 px.
- Working area equals the full bounds on both, so the taskbar is auto-hidden
  and the screen bottom *is* the floor.

**Consequences:**
- **She can walk straight across at floor level.** The floors of the two
  monitors are essentially continuous at the right edge of the ultrawide
  (a 3 px step, invisible).
- **The 2×2 grid on DISPLAY2 gives three ledges per screen.** The tops of the
  two bottom quadrants sit at y ≈ 357 + 540 = 897, in the middle of the screen,
  and the seam between the quadrants runs across the full 1920 px width. The
  tops of the top quadrants are at the screen top, so they're unusable. With
  the grid, **the "clear space above" rule has to change**: every mid-screen
  ledge has a window directly above it. New rule: she may visually overlap
  *non-focused* windows above her ledge, but never the focused one. If the
  window above the seam is the focused one, that ledge is off-limits until
  focus moves.
- **The overlay can't simply span both monitors again.** main.gd's own history
  says `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING` exists because one transparent
  window across both monitors caused an **AMD Vulkan device-lost crash** on
  the RX 6700. Recommended architecture, which the rest of I-5 builds on:
  **a follow-window.**
  - The overlay window shrinks to her bounding box plus margin (at 60 %, about
    450×450 px). The camera is fixed inside it; *moving her = moving the
    window* (`window_set_position` per frame, in virtual-desktop pixels).
  - This removes the giant transparent surface (the likely crash trigger, and
    a real GPU/compositor cost on a 3440 px + 1920 px desktop). Crossing
    monitors becomes free: it's just window coordinates. Platform coordinates
    need no conversion: window rects and her position are in the same pixel
    space.
  - Costs: the camera framing and the walk code get reworked (her world
    position becomes the window position, and the skeleton stays centred).
    Big moves like falls and jumps move the window quickly, which should be
    smooth on Windows but needs a real check. The click-through patch and the
    `WDA_EXCLUDEFROMCAPTURE` idea apply unchanged.
  - Rejected alternatives: re-testing the full-span window (it may crash the
    GPU driver again), or one overlay per monitor with a hand-off between
    them (two processes, a visible seam, twice the state to keep in sync).
- **DPI**: both monitors report at 100 % scaling (bounds match native
  resolution), so one pixel unit covers both. If scaling on either monitor
  ever changes, window-rect handling has to become per-monitor-DPI-aware.
