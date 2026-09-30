# WP-54 — Voice v2: IndexTTS + RVC -4, moods, sentence streaming

Read `00-implementer-context.md` first. **Repos:** felt-voice (done),
felt-core, felt-tray, felt-animation. **Machines:** Nitro5 (voice), server
(felt-core), desktop (tray + animation). **Size:** L.

## Decided (2026-09-29, Mario, by ear)

- After a long A/B (Kokoro, GPT-SoVITS, IndexTTS-2.5, VoxCPM2, OmniVoice,
  AuK, Seed-VC; clips under `E:\Felt\scratch\voice-test\`):
  **IndexTTS-2.5 reading with Teto's own (Japanese) reference clip, then the
  existing Teto RVC model at pitch -4**. Mario: "-4 is the way, idx -4".
  - Rejected: generic TTS voices ("sound like generic youtube voice overs"),
    GPT-SoVITS alone ("too child like"), Seed-VC (weirder than RVC), English
    reference clips for GPT-SoVITS ("I cant understand a word").
- Moods: felt-core's emotion words map onto IndexTTS's emotion vector.
- It runs on the Nitro5's RTX 3060 (no €200 GPU). The laptop becomes a
  voice box: felt-voice (STT + RVC) + felt-indextts. The brain moves to the
  server's P104 (WP-36).

## Done: felt-voice (`d2e1f55`, 2026-09-29)

- `FELT_VOICE_TTS_ENGINE=indextts`, `FELT_VOICE_RVC_PITCH=-4`. `/v1/tts`
  takes an optional `emotion`.
- The **felt-indextts** service (`indextts_service/server.py`,
  `127.0.0.1:8431`, its own venv in `~/felt-indextts`) returns base audio,
  and felt-voice applies RVC.
- **VRAM:** 4.8 GB peak of 6 GB. IndexTTS's 2.2 GB reference encoder runs on
  the CPU, once per reference.
- **Measured, whole lines:** 6.1 s for 83 chars (excited), 10.8 s for 97
  chars (sleepy). A line takes about its own duration. The first sentence
  alone (~3 s of audio) takes ~3.7 s, which is why the rest of this WP
  exists.

## To build: sentence streaming for prompted replies

Scope:
- **Streamed:** `/v1/voice-chat` and `/v1/text-chat`, the replies Mario
  asked for. The wait is noticeable there.
- **Not streamed:** screen reactions, event lines and proactive lines
  (unprompted, and they arrive whole).

### Protocol

1. **felt-core** splits the TTS text into chunks (`speech_chunks()`):
   - sentence boundaries `. ! ? …` plus newlines;
   - a chunk under ~25 chars merges into the next;
   - the first chunk aims for ≥ 40 chars so it isn't a lone "Hm.";
   - one chunk means no streaming: the response is exactly as today.
2. With ≥ 2 chunks, felt-core synthesises chunk 0 and answers the request
   as today:
   - the WAV of chunk 0;
   - `X-Reply-Text` = the **full** reply, plus the usual headers;
   - `X-Reply-Stream: <id>` (a uuid4 hex) and `X-Reply-Chunks: <N>`.

   A background task then synthesises chunks 1..N-1 in order into an
   in-memory store (the TTL is below).
3. `GET /v1/reply/{id}/chunk/{n}?timeout=30` long-polls:
   - **200** + WAV + `X-Chunk-Text` once chunk n is ready;
   - **204** if n ≥ N (done);
   - **404** for an unknown or expired id;
   - **502** if that chunk's TTS failed. The tray stops the stream.
4. **felt-tray**, after its normal `/reply_ready` for chunk 0:
   - loops n = 1..N-1: GET the chunk, then POST felt-animation
     `/reply_append` (multipart `audio`, `text`);
   - stops on 204, 404 or 502, or when the next reply starts;
   - on a timeout, logs and stops.
5. **felt-animation** `/reply_append`:
   - queues the chunk behind the reply currently speaking;
   - runs Rhubarb on arrival, in parallel with the current playback;
   - when the current audio ends, sends that chunk's lipsync cues and
     starts its audio back to back, the same "one synchronized start" as
     `handle_reply`;
   - plays **no new reaction or pose** (the reply's own ran at chunk 0), but
     keeps the face and gaze "speaking" and the bubble visible until the
     last chunk ends;
   - drops appends if the parent reply was hushed, the queue was cleared
     (a new `reply_ready`, "stop"/hush, presence away), or none is active.

### Details

- `emotion` reaches felt-voice: the TTS request body gets `"emotion": <mood>`
  whenever felt-core has one (screen reactions, event lines, proactive
  lines). Chat replies have none yet, so they speak neutrally.
- `tts_cache` is keyed on (text, emotion).
- Stream store:
  - entries expire 120 s after the last chunk is done or after creation;
  - at most 8 live streams, oldest dropped;
  - no disk.
- Config (non-secret, in `.env.example`): `FELT_REPLY_STREAMING=true`,
  `FELT_REPLY_STREAM_FIRST_CHUNK_CHARS=40`.
- Metrics: `tts` stage per chunk, plus `tts_first_chunk` for chunk 0.

## Accept

1. A 3-sentence reply to a typed chat message starts playing within
   **≤ 5 s** of the reply text existing (chunk 0 ≈ 3.7 s), then plays to
   the end with no gap longer than ~1 s between sentences.
2. Lipsync follows every chunk. Reaction and face run once. The bubble
   stays until the end.
3. Saying "stop" or hush mid-reply stops the remaining chunks.
4. A one-sentence reply behaves exactly as before, with no stream headers.
5. Screen reactions and event lines speak with their mood (hear sleepy vs
   excited).
6. All three repos' tests are green, and ruff and ty are clean.

## Laptop services (Mario's sudo, once)

```
sudo cp ~/felt-voice/deploy/felt-indextts.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now felt-indextts
sudo systemctl restart felt-voice
```

Rollback: `FELT_VOICE_TTS_ENGINE=chatterbox` and `FELT_VOICE_RVC_PITCH=0` in
`~/felt-voice/.env`, then restart felt-voice. The previous `.env` is saved
as `.env.bak-chatterbox-20260929`.

## Mood strength (2026-09-30, felt-voice `d743e7d`)

- **Symptom (Mario):** with moods on, she "always sounds like she's
  exclaiming something".
- **Cause:** the emotion vectors went to IndexTTS raw. IndexTTS mixes
  `presets × sum + reference voice × (1 − sum)`, and amused summed to 0.9,
  so 90% of the delivery was a stock emotion preset. Amused is also the
  most-used mood (59 of the last ~110 lines).
- **Fix:** felt-indextts now passes each vector through IndexTTS's own
  `normalize_emo_vec`, which biases down surprised and calm and caps the
  sum at 0.8, then scales it by **0.6**. Mario picked 0.6 by ear from now /
  100% / 60% / 35% takes of all eight moods ("60% for normal mood"). Amused
  now sums to 0.43.
- Settings: `FELT_INDEXTTS_EMOTION_NORMALIZE` (default true) and
  `FELT_INDEXTTS_EMOTION_STRENGTH` (default 0.6). Both `/v1/tts` and `/tts`
  accept per-request `emotion_strength` and `emotion_normalize` overrides
  for A/B tests.
