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

## Notes from implementation (2026-09-22)

Code done, committed, deployed, and checks 1-2 verified live. **Check 3
needs Mario** (see below) - not ticked in the README yet.

Commits: felt-core `85a31c4` (deployed via `/home/clockmost-infra`
`ea4f1a1` + `clockmost-deploy.service`, "OK — deployed felt-core"),
felt-tray `9af902a` (not yet relaunched - see check 3).

- `felt_core/metrics.py`: ContextVar-scoped `_RequestMetrics`
  (request_id/endpoint/db_path/session_id/stages), `start_request`,
  `timed()`, `record()`, `server_timing_header()`, `compute_stats()`
  (linear-interpolation p50/p95, `by_route`/`by_skill` breakdowns).
  `db.py` gained the `latency` table + `save_latency_row`/
  `get_latency_rows`/`delete_old_latency_rows` (pruned >30 days on
  startup, wrapped in try/except so a prune failure can't block startup).
- `api.py`: a `@app.middleware("http")` on `/v1/*` only, creates the
  request_id, times `total`, stamps `Server-Timing` (added to CORS
  `expose_headers`), and `GET /v1/metrics/latency`. `stt`/`tts` wrapped
  there; `tts` tagged with `chars=len(stripped_text)` (the actual TTS
  input after WP-03's `strip_for_tts`, not the raw reply length).
- `brain.py`: `router` wraps `decide_tool`; `privacy` wraps the WP-03
  concurrent task via a small `_timed_privacy_check` helper (proves
  `contextvars.copy_context()`, which `asyncio.create_task` uses, carries
  the request's metrics context into that task correctly - verified both
  by a unit test and live, see below); `skill` tagged `skill=<name>`;
  `reply` tagged `route=cloud|local, model=...` at both `_chat_reply`'s
  branches and the tool-result reply call; `screen_reaction` likewise in
  `process_screen_context`.
- felt-tray: `VoiceChatResult.server_timing` carries the header through;
  `_format_server_timing()` parses it into the WP's example short form
  (verified directly: fed the WP's own example header through it, got
  back exactly `[router 3.8, reply(cloud) 0.6, tts 2.4]`); `_finish_voice_chat`
  adds `hotkey_release_to_audio` (timestamped at the actual moment the
  recorder stopped, before STT/upload even starts - "the number Mario
  actually feels," not "request sent"); `_on_screen_context` gets the
  same `upload_to_response`/`response_to_playback`/`server=[...]` line,
  no hotkey timestamp (nothing to time from - it's not user-triggered).

**Live baseline** (check 2, session `wp04-test`, `since_hours=1`,
2026-09-22 ~21:38, n=3-4 depending on stage):

| stage | p50 | p95 | max |
|---|---|---|---|
| privacy | 10.4s | 12.2s | 12.4s |
| router | 10.9s | 12.7s | 12.9s |
| skill (get_weather) | 2.2s | - | 2.2s |
| skill (get_time) | 0.0s | - | 0.0s |
| reply, local | 57.0s | 57.5s | 57.6s |
| reply, cloud | 0.6s | - | 0.6s |
| tts | 9.6s | 15.3s | 16.0s |
| **total** | 42.7s | 84.1s | 87.2s |

**This is dramatically worse than the WP's own hand-measured baseline**
(router 3.8-4.9s, local phrasing 17.4s, total weather turn 33s) - router
alone is now ~2.5x that, and local reply generation is ~3.3x. Whatever
this WP's numbers are *for* (the next speed decision), that decision
needs to start from "something changed since 2026-09-22's hand-measured
baseline, on the Nitro5 side (Ollama load? a model swap for ComfyUI? a
resource contention issue?)," not from the original 33s figure - this
wasn't visible before because nobody was measuring, exactly the gap this
WP closes. Flagging for Mario rather than investigating further - WP-04
is instrumentation, not a fix, and root-causing Nitro5 slowness is a
different WP's job.

One self-referential quirk, not fixed (out of scope, harmless): a call to
`/v1/metrics/latency` itself matches the `/v1/*` middleware and gets its
own `total` row (no other stages, since that endpoint doesn't call
`timed()`) - so back-to-back queries see `total`'s `n` creep up by one
per previous query. Doesn't affect router/reply/tts/skill stats at all,
only `total`'s own count.

**Still needed - Mario**: check 3 (relaunch felt-tray with the WP-04
build, do one real voice-hotkey turn, confirm `%TEMP%\felt-tray.log`
shows a `turn timing: ...` line with `hotkey_release_to_audio` on it).
felt-tray isn't rebuilt/relaunched yet - only committed and pushed. Say
the word and I'll relaunch it (or if you'd rather do the hotkey press
yourself on your own schedule, just ping me after and I'll check the
log).
