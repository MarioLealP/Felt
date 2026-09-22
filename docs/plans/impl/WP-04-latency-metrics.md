# WP-04 — Latency metrics end to end

**Repos**: `E:\Felt\felt-core` (deploy), `E:\Felt\felt-tray`. **Size**: M.
**Depends on**: WP-03.

## Why

Every later speed decision (TTS engine, caching, model choice, the Nitro5
Ollama/ComfyUI state) should be made from real numbers. Today they come from
hand-correlating log timestamps. Baseline measured by hand on 2026-09-22:

| Stage | Time |
|---|---|
| router | 3.8–4.9 s |
| weather fetch | 0.29 s |
| local skill phrasing | 17.4 s |
| TTS | 12 s |
| Gemini reply | ~0.6 s |
| **total, weather turn** | **33 s** |

## Changes

### felt-core: `felt_core/metrics.py`
- A `ContextVar` holding the current request's `request_id` and a list of
  `(stage, ms)`.
- `@asynccontextmanager async def timed(stage: str, **tags)` records the
  elapsed ms to that list and to a new SQLite table:
  ```sql
  CREATE TABLE IF NOT EXISTS latency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL, endpoint TEXT, stage TEXT NOT NULL,
    ms REAL NOT NULL, route TEXT, skill TEXT, model TEXT, chars INTEGER,
    session_id TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
  )
  ```
  Keep writes cheap (one insert per stage) and never let a metrics failure
  break a request (wrap in try/except + log).
- FastAPI middleware:
  - creates the `request_id` for `/v1/*` routes;
  - records a `total` stage;
  - adds a standard **`Server-Timing`** header
    (`router;dur=3812.4, reply;desc="cloud";dur=612.0, tts;dur=2430.1, total;dur=7021.9`).

  Add `Server-Timing` to the CORS `expose_headers`.
- Wrap these stages:
  - `stt` (voice-chat)
  - `router` (the `decide_tool` call)
  - `privacy`
  - `skill` (with `skill=<name>`)
  - `reply` (with `route=cloud|local`, `model=…`)
  - `tts` (with `chars=len(text)`)
  - `screen_reaction` (the model call in `process_screen_context`)
- `GET /v1/metrics/latency?since_hours=24&endpoint=` returns, per stage, `n`,
  `p50`, `p95` and `max` in ms, plus `route`/`skill` breakdowns. Compute them
  in Python from the rows; the volume is tiny.
- Retention: delete rows older than 30 days on startup.

### felt-tray: client-side timing
- In `_finish_voice_chat` and `_on_screen_context`, measure:
  - `upload_to_response` (request sent → response received), and
  - `response_to_playback` (response received → `play_wav` returned; this
    moves to felt-animation in WP-08, so keep it simple).
- Log one line per turn at INFO:
  `turn timing: total_client=7.4s server=[router 3.8, reply(cloud) 0.6, tts 2.4] upload_to_response=7.1s`
  (parse `Server-Timing`).
- For voice, also log the hotkey-release timestamp →
  `hotkey_release_to_audio`. That's the number Mario actually feels.

## Tests
- felt-core `test_metrics.py`:
  - `timed()` records into the table and the context list;
  - the `Server-Timing` header is present on a `TestClient` request to
    `/v1/chat`, with router/reply fakes monkeypatched;
  - the percentile endpoint returns correct p50/p95 for seeded rows.
- The suite stays green.

## Deploy + acceptance
1. Deploy. Then send 3 `/v1/text-chat` calls with session `wp04-test`: the
   weather, a joke, a time question.
2. `curl http://192.168.1.110:8420/v1/metrics/latency?since_hours=1`
   shows router/reply/tts/total with sensible numbers.
3. Relaunch felt-tray, do one real voice turn (Mario presses the hotkey, or
   ask him to), and check `%TEMP%\felt-tray.log` for the `turn timing` line.
4. Put the numbers from step 2 into this WP's notes as the new baseline.
