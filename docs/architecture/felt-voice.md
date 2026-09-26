# felt-voice

## Purpose

Local STT (faster-whisper) + TTS (Chatterbox-Turbo or Piper fallback), both re-voiced via Kasane Teto RVC. Runs on Nitro5 laptop (separate hardware, 6GB VRAM shared with Ollama). No audio leaves the LAN.

## Runtime

- **Host:** Nitro5 laptop (192.168.1.xxx)
- **Port:** 8421 (http://0.0.0.0:8421)
- **Launch:** systemd service (`felt-voice.service`) → `uv run felt-voice-serve`
- **User:** benylin (scoped NOPASSWD sudo via sudoers allowlist)
- **WD:** /home/benylin/felt-voice
- **Dependencies:** HuggingFace models (cached locally, HF_HUB_OFFLINE=1), CUDA for Chatterbox/RVC

## Module Map

| File | LOC | Responsibility |
|------|-----|---|
| src/felt_voice/api.py | 103 | FastAPI endpoints (/v1/tts, /v1/stt, /v1/gpu-status), lifespan warmup |
| src/felt_voice/tts.py | 91 | Chatterbox/Piper synthesis, tag stripping, silence generation |
| src/felt_voice/config.py | 65 | VoiceConfig pydantic settings, env var loading |
| src/felt_voice/rvc.py | 64 | Kasane Teto voice conversion (infer-rvc-python wrapper) |
| src/felt_voice/chatterbox_engine.py | 56 | Chatterbox-Turbo init, low-VRAM mode, fallback logic |
| src/felt_voice/tags.py | 45 | [sigh]/[laugh] tag handling, ALLOW_TAGS gate |
| src/felt_voice/stt.py | 27 | faster-whisper transcription wrapper |
| src/felt_voice/gpu_stats.py | 38 | GPU memory queries (nvidia-ml-py) |
| src/felt_voice/__init__.py | 2 | Package init |
| revoice_batch.py | 53 | Standalone batch re-voice script (WP-19 offline work) |

**Tests:** 5 files (test_tts.py, test_stt.py, test_rvc.py, test_tags.py, test_gpu_stats.py)

## Interfaces

| Endpoint | Method | Input | Output | Notes |
|----------|--------|-------|--------|-------|
| /v1/tts | POST | `{"text": "..."}` | audio/wav bytes | Chatterbox→RVC; fallback Piper on error |
| /v1/stt | POST | multipart (wav file) | `{"text": "..."}` | CPU int8 by default |
| /v1/gpu-status | GET | — | `{"available": true/false, ...}` | Memory stats if CUDA present |

## Config

| Env Var (FELT_VOICE_ prefix) | Default | Purpose |
|-----|---------|---------|
| WHISPER_MODEL | base.en | STT model (CPU int8 by default) |
| WHISPER_DEVICE | cpu | "cuda" or "cpu" |
| TTS_ENGINE | chatterbox | "chatterbox" or "piper" |
| CHATTERBOX_REF_WAV | ./models/chatterbox/teto_ref.wav | Reference clip for zero-shot cloning |
| CHATTERBOX_DEVICE | cuda | "cuda" or "cpu" |
| CHATTERBOX_LOW_VRAM | true | bf16 T3, conditioning on CPU (Nitro5 tight fit) |
| ALLOW_TAGS | false | Keep [sigh]/[gasp] (false strips; live path) |
| PIPER_VOICE | en_US-lessac-medium | Piper voice ID |
| PIPER_VOICES_DIR | ./voices | Piper voices cache |
| RVC_MODEL_PATH | (unset) | Optional Teto RVC model path |
| RVC_INDEX_PATH | (unset) | Optional RVC index |
| RVC_ONLY_CPU | true | RVC on CPU (avoid VRAM conflict with Ollama) |
| HOST | 0.0.0.0 | Listen address |
| PORT | 8421 | Listen port |
| HF_OFFLINE | true | No HuggingFace Hub checks |

Set via .env (see .env.example).

## Tests

**Safe (don't load GPU models):** test_gpu_stats.py, test_tags.py (tag stripping logic)
**Verified end-to-end (2026-09-11):** real TTS→STT round-trip via HTTP API, not scripts

## Smells

- **Hardcoded relative paths** (./models/chatterbox/teto_ref.wav, ./voices) — breaks if pwd changes; should resolve to repo root
- **WP-19 reference in config** (config.py:25, tags.py) — part of active code, not historical (actually OK)
- **revoice_batch.py is standalone** (53 LOC) — batch offline script, not integrated into api.py; separate CLI entry point
- **No systemd watchdog** — service restarts on failure but no heartbeat monitoring
- **FELT_VOICE_RVC_MODEL_PATH optional** — if unset, plain Piper output; no warning logged if missing when expected
- **Low-VRAM mode comment outdated?** (config.py:50-52) — states 2026-09-12 measurement; no re-check since

## Ranked Suggestions

1. **Resolve hardcoded paths to repo root** (S, agent-ok) — use __file__ or pathlib to find ./models, ./voices relative to src root
2. **Add /v1/readiness endpoint** (S, agent-ok) — signal when TTS/STT engines fully loaded (block requests until warm)
3. **Log RVC skip reason** (S, agent-ok) — if RVC_MODEL_PATH unset, log "RVC disabled, using plain Piper" on startup
4. **Integrate revoice_batch.py** (M, no) — batch endpoint /v1/batch-revoice, or separate CLI tool with shared config
5. **Add systemd watchdog** (M, no) — periodic /v1/health POST to systemd, or liveness probe
