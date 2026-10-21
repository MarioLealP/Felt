# WP-65 — Streamed replies: she starts talking while she's still writing

Read `00-implementer-context.md` first. Builds on **WP-54** (sentence-chunked audio).
**Repos:** felt-core (main work), felt-tray-rust, felt-dashboard, felt-animation (client side of the
protocol change). **Machines:** server (felt-core, felt-llm), desktop (tray + animation), phone (app).
**Size:** L. Plan written 2026-10-20 (Claude, model-spike session); build in a fresh session.

## Why

Measured 2026-10-20, warm, production Bonsai 2 27B (workspace `runbooks/felt-model-spike.md`):
"what should I make for dinner tonight? I have rice, eggs and some leftover chicken"
-> felt-core `chat()` **9.8 s** for the whole 3-paragraph reply, then first sentence TTS 0.6 s + RVC 1.3 s
-> **her voice starts ~11.7 s after the message**. Bonsai generates ~17 tok/s at chat depth; the first
sentence is ready after ~1-2 s of generation. Goal: **first audio ~3-4 s** after the message.

## Today (what WP-54 built)

- `api.py::_synthesize_reply` (stream=True on `/v1/voice-chat` + `/v1/text-chat`): the finished reply is
  split by `speech_chunks(tts_text, reply_stream_first_chunk_chars=40)`; chunk 0's audio goes back in the
  response with `X-Reply-Text` (**full text**), `X-Reply-Stream` (id) and `X-Reply-Chunks` (**count**);
  `_fill_reply_stream` synthesises the rest; clients long-poll `GET /v1/reply/{id}/chunk/{n}`
  (200 WAV + `X-Chunk-Text`, 408 not ready, 204 past the end, 502 TTS failed). `reply_streaming=True`.
- Clients reading the headers: `felt-tray-rust/src/core.rs` (`stream_fields(X-Reply-Stream,
  X-Reply-Chunks)`), `felt-dashboard/src/lib/api.ts` (`ReplyStream {id, chunks}`, needs chunks >= 2),
  `felt-animation/.../routers/playback.py`, old `felt-tray` (Python, retiring).
- The gap: `chat()` (`brain/orchestrator.py`) returns only when the whole reply exists - `local_llm.chat`
  is a non-streaming call. Everything above starts after that.

## Decided (Mario, 2026-10-20)

- **Build it** ("yeah lets get streaming going").
- **Fake-claim guard - option 1** ("go with 1"): today `orchestrator.py` (~l.302) checks the finished reply
  with `lookup_claims.claims_an_action / claims_a_lookup` and retries with `tool_choice="required"`.
  Streaming speaks before the full text exists, so:
  - **Check the first sentence before it's spoken** (the common fake claims are up front: "Done.",
    "Set for 7:30.", "Milk's on there."). A hit -> don't speak it; fall back to today's path (finish,
    guard, retry with a tool) for this reply.
  - **The full text is still checked at the end.** A late hit -> she corrects herself out loud in her own
    words (via her LLM, memory `felt-everything-through-her-llm`), e.g. "wait, I didn't actually set
    that - doing it now", and the retry runs. Rare by design.
- Only `/v1/voice-chat` + `/v1/text-chat` stream (WP-54's scope). Screen reactions, event/proactive lines,
  alert lines stay whole.

## Design

1. **felt-llm streaming call** - `local_llm.chat_stream(...)`: `stream: true` on llama-server's
   `/v1/chat/completions`, yields text deltas; tool-call deltas are collected whole (a reply that turns
   into a tool call isn't spoken; the tool round runs as today, then the *final* answer streams).
   Thinking stays off (`--reasoning off`), so no reasoning deltas to filter on chat.
2. **Orchestrator** - a `chat_streamed()` sibling of `chat()` (don't fork the logic: share the tool loop,
   guards, history writes, memory/marks). It yields sentence chunks as they complete (same splitter rules
   as `speech_chunks`: first chunk >= 40 chars or a sentence end, then sentences), and finishes with the
   full `ChatResult` (reply, ui_action, animation_tag, emotion) - history is written once, at the end.
   First-sentence guard before chunk 0 is released; full-text guard at the end (see Decided).
3. **API** - `_synthesize_reply` gets a live source instead of a list: chunk 0 is TTS'd the moment it
   exists and returned; later chunks are appended to the `reply_stream` as they arrive.
   **Protocol v2** (count + full text aren't known at response time):
   - `X-Reply-Stream: <id>`, `X-Reply-Chunks: open` (instead of a number), `X-Reply-Text` = chunk 0's
     text only, plus `X-Reply-Stream-Version: 2`.
   - `GET /v1/reply/{id}/chunk/{n}`: unchanged (200 / 408 / 204 when the reply ended / 502).
   - New `GET /v1/reply/{id}` -> JSON `{done, text, ui_action, animation_tag, emotion}` once finished
     (clients that show text or run the UI action / animation tag read it here).
   - Clients without v2 support: a header/flag per request (`X-Accept-Stream: 2`) - without it,
     felt-core falls back to today's behaviour, so each client can be updated separately.
4. **Clients** (each one PR, each tested against a felt-core that supports both):
   tray-rust (play chunks until 204, then fetch `/v1/reply/{id}` for text/ui_action/tag),
   dashboard/app (same in `api.ts`), felt-animation playback (same).
5. **Voice side unchanged** for this WP - felt-voice keeps doing `/v1/tts` per chunk. (Separately, the
   voice stack is moving to the server: Chatterbox-Turbo "lite" + Teto RVC beside Bonsai - see the spike
   runbook section 9 + "voice" notes; RVC on the 1660 needs long sentences split or a little more VRAM.)

## Test plan

- Unit: splitter on streamed deltas == `speech_chunks` on the whole text; first-sentence guard catches
  the e2e fake-claim phrasings ("Set for 7:30.", "Done. Milk's in there.", "ringing it now"); history
  written once with the full reply.
- felt-core `tools/e2e_chat.py` (--repeat 3) must stay at Bonsai's 246/249 or better, through the
  streamed path (add a `--stream` switch that consumes `chat_streamed()`).
- Timer (workspace `runbooks/spike-scripts-2026-10/`, `chat_timer.py`-style): time to chunk 0 text, to
  chunk 0 audio, to the full reply - before/after. Target first audio <= 4 s warm.
- Live: Mario on the tray + phone; each client updated and checked before the next.

## Order

felt-core streaming call + `chat_streamed()` + tests -> API v2 behind `X-Accept-Stream: 2` (old clients
untouched) -> tray-rust -> dashboard -> animation -> e2e + timer -> Mario's live check.

## Log

- 2026-10-20: planned (Claude). Context: Bonsai 2 27B on the fork image (infra #396/#399), 32K, one slot;
  warm chat 9.8 s for a long reply; first-sentence voice 1.9 s (Turbo lite 0.6 + RVC 1.3).
- 2026-10-20: **step 1 built** (felt-core branch `benylin/wp65-stream`, clone `~/src/felt-core-stream`):
  `local_llm.chat_stream()` (SSE checked against the real felt-llm: OpenAI deltas, tool-call pieces by index,
  timings on the last event), `speech.SpeechChunker`, `brain/streaming.py` (`ReplySpeaker`, `correction_note`),
  `orchestrator.chat_streamed()` sharing `chat()`'s turn (`_reply_turn` at the three answer calls, `_said` at
  every history write). Guard option 1 as decided: every chunk inside the guard window (first 160 chars) is
  checked before release - so a claim in chunk 1 isn't said either; a late hit puts `correction_note` into the
  tool-result message so the follow-up reply corrects her in her own words. `lookup_claims` gained the bare
  openings from the plan's test list ("Done.", "Set for 7:30", "Milk's in there", "ringing it now", "Dimmed to")
  - today's guard missed all of them; this also tightens plain `chat()`.
  Deviations: the splitter works on the reply as written (newlines are sentence ends; the API strips each
  chunk for TTS), and a short tail after chunk 0 becomes its own chunk (chunk 0 is already out) - else equal
  to `speech_chunks`. Paths that don't stream (HA, presence, weather fast line, email summary) come out in
  chunks at the end. e2e: `tools/e2e_chat.py --stream`. Timer `spike-scripts-2026-10/stream_timer.py`
  (warm, dinner question): **first chunk 2.1-2.4 s vs 7.8-12.4 s for the whole chat()**; rounds that queued
  behind live Felt prompts on the one slot hit 11-43 s (cache eviction - the "warm her prompt / cache-ram"
  follow-up in the spike handoff).

- 2026-10-21: **step 2 built** - API v2 behind `X-Accept-Stream: 2` as designed (`reply_stream.open_stream` with
  `append`/`end` + a long-poll that waits for a chunk still being written, `GET /v1/reply/{id}`; no header =
  WP-54 unchanged; no chunks / felt-voice down = the whole-reply response; felt-llm gone mid-reply = stream
  ends, `/v1/reply/{id}` carries `error`). felt-core PR #49 (steps 1+2). e2e `--stream`: 56/56 ok on a partial run
  (the x3 run was stopped - Mario: "just skip the other e2e"). Timer `spike-scripts-2026-10/sound_timer.py`
  (prompt -> first WAV in hand, warm, live felt-core stopped so the slot was quiet - Mario: "just kill felt core"):
  **v2 8.8-10.7 s vs v1 10.1-23.9 s**; text ready v2 2.3-2.6 s vs v1 3.6-13.3 s; **chunk 0's TTS on the laptop's
  felt-voice is 6-8 s (74-97 chars)** - the rest of the gap to the 4 s target is the voice (server voice stack:
  ~1.9 s in the spike), or a shorter first chunk (`reply_stream_first_chunk_chars`, 40 today). Next: tray-rust.
- 2026-10-21 (night, paused - Mario off to sleep): live = felt-core #49 + #50 (ReplyMeta: a skill's tag /
  ui_action on chunk 0; first chunk may end at a clause break). Voice on the server built + tested
  (felt-voice #4 + #5, image `clockmost/felt-voice:a3adb81fb292`, models `/home/ai-models/voice`): fits both
  cards beside Bonsai 32K, no OOM in the worst case. Timer, message -> first sound, server voice: **~6-7 s
  typical** (best 5.7). **Open:** (1) infra #402 (felt-voice stack + felt-core -> `http://felt-voice:8421`)
  waits for Mario's merge - then turn the laptop off (ComfyUI goes with it); (2) tray `pkgs/felt-tray` main
  has the v2 change (commit 25cb9ee, vetted bumps) - cut `./release.sh 0.9.0`, `pacman -Syu`, install log,
  Mario's live check; (3) dashboard needs nothing (app chat is text-only `/v1/app/chat`); felt-animation
  has no chat calls on Linux - nothing to change; (4) faster than ~6 s needs less GPU contention while
  Bonsai still writes.
