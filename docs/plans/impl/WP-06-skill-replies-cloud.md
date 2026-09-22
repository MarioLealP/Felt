# WP-06 — felt-core: skill replies phrased in the cloud (result-gated), weather cache + precompute

**Repo**: `E:\Felt\felt-core` (server, so deploy). **Size**: M. **Depends
on**: WP-05.

## Why

Measured turn for "what's the weather right now?": **33 s**. The fetch was
0.3 s; **local llama3.1:8b phrasing took 17.4 s** (the Nitro5's 6 GB VRAM is
shared with ComfyUI, so the 8B model partly runs on CPU), and TTS of a long
reply took 12 s. Gemini/Gemma phrase in ~0.6 s. Today every skill reply is
forced local.

Mario's privacy rule (decided 2026-09-22): **fetching data always stays
local; the result text may be phrased in the cloud** once it's known not to
be sensitive. His words: "stuff like your shelf light is on isn't private,
but fetching the data is." Also: "Google already has my email and calendar
so that's fine, same with alarm, shopping list and music."

## Changes

### 1. Per-skill privacy class (`plugins/skills.json`, next to `tags.json`)
```json
{
  "_comment": "public = straight to cloud; google_ok = straight to cloud (Mario: Google already has it); gated = result text goes through the local privacy classifier first; local = never leaves. Unlisted skills default to 'local' (fail closed).",
  "get_weather": "public", "get_time": "public", "news_digest": "public",
  "web_search": "public", "poe_price_check": "public", "generate_image": "public",
  "check_email": "google_ok", "list_calendar_events": "google_ok", "create_calendar_event": "google_ok",
  "set_alarm": "google_ok", "set_timer": "google_ok", "list_alarms": "google_ok", "cancel_alarm": "google_ok",
  "shopping_list": "google_ok", "play_music": "google_ok", "media_control": "google_ok",
  "smart_home_control": "gated", "get_phone_battery": "gated", "get_container_status": "gated",
  "get_recent_alerts": "gated", "get_gpu_status": "gated", "printer_status": "gated", "delegate_research": "gated",
  "search_documents": "local", "remember_fact": "local", "find_phone": "local"
}
```
Load it in `plugin_loader` into `LoadedSkill.privacy` (default `"local"`).
Also add a `plugins/README.md` note: every new skill needs an entry, or it
stays local.

### 2. Phrasing path in `brain.chat` (the skill branch)
- `text_for_voice = result.voice_line or result.text`. `SkillResult.voice_line`
  exists already and nothing reads it. Wire it: `voice_line` is the spoken
  form, `text` is the full form (for the toast/chat).
- Decide the route by class:
  - `public` / `google_ok` → cloud.
  - `gated` → `is_safe_for_cloud(tool_output)` → cloud if SAFE, else local.
  - `local` → local.
- Cloud: `cloud_generate("skill_phrasing", system=_PERSONALITY_PROMPT +
  mood/tone line (WP-15 adds it; for now just personality), messages=[last 3
  exchanges from history (only if the whole window passes
  is_safe_for_cloud) + user message + a tool-result turn], max_tokens=120)`.
  Use the same instruction as WP-03 (one or two spoken sentences, lead with
  the answer, one bit of personality if it fits, never invent anything not
  in the tool result). **Never** send facts.
- On `CloudUnavailable` or an error → the existing local path (with WP-03's
  length cap).
- `_summarize_pending_email` → `cloud_generate("summary", …)` (email is
  `google_ok`), with a local fallback.
- `privacy.py`: update `_PRIVACY_PROMPT` to match Mario's line. Remove "the
  contents of emails, calendar events" from the PRIVATE list; keep
  documents, health, finance, credentials, home-infra names, people's
  personal details, and remembered facts. Add worked examples:
  `"your shelf plug is on"` → SAFE, `"Dentist Tuesday 3pm"` → SAFE,
  `"<a paragraph from a medical document>"` → PRIVATE.

### 3. Weather cache + precomputed answer
- In `plugins/get_weather/skill.py`: a module-level cache of the Open-Meteo
  JSON keyed by `(lat, lon, unit)`. **Current conditions TTL 20 min**; daily
  forecast parts are fine for up to 3 h (one call returns both; just keep the
  timestamp). Mario suggested 12 h. That's too stale for "right now" (a
  morning fetch answering an evening question), and the fetch only costs
  0.3 s anyway, so the real win is below.
- Background task in `api.lifespan`: every 15 min, refresh the weather cache,
  then **precompute the spoken "current weather" line** through
  `cloud_generate("skill_phrasing", …)` and **pre-render its TTS**. Store
  `(line, wav_bytes, animation_tag, computed_at)` in memory.
- Fast path in `chat()`: if the router (or the WP-03 guard table's
  counterpart) picked `get_weather` with day in {now/current/today-now…}
  and the precompute is < 20 min old, return that line. The API layer then
  serves the cached WAV instead of calling felt-voice.
- To do that cleanly, add a tiny **TTS cache** in `api._synthesize_reply`: an
  LRU (64 entries) keyed by `sha256(stripped_text)`. The precompute warms it
  by calling the same function, so the fast path is simply a cache hit.

### 4. Measure
Everything is inside `timed()` already (WP-04). Record before/after in the
notes.

## Tests
- plugin_loader reads `skills.json`; an unknown skill → `local`.
- The class → route matrix, with fakes for `cloud_generate` /
  `is_safe_for_cloud` / `_ollama_chat`. Facts never appear in cloud messages.
  A `local` skill never calls cloud even if everything says SAFE.
- `voice_line` preferred for phrasing.
- The weather cache TTL (freeze time).
- The fast path returns the precomputed line and makes zero model calls; the
  TTS cache hit makes zero felt-voice calls.

## Deploy + acceptance
1. Session `wp06-test`: "what's the weather right now?", three times, a
   couple of minutes apart. The first may be a normal cloud path; after the
   precompute has run, **total server time < ~2 s** (see
   `/v1/metrics/latency`). The line is short and has personality.
2. "What's on my calendar today?" → `/v1/metrics/cloud` shows
   `skill_phrasing` +1, no local phrasing in the log.
3. "Is the shelf plug on?" (gated) → the log shows the privacy check, then
   cloud.
4. "Find my notes about <anything>" (`search_documents`) → local only, and
   the log proves no cloud call.
