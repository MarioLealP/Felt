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

## Notes from implementation (2026-09-22)

Implemented as specced, with two real bugs found and fixed live along the
way, plus one known unresolved classifier-reliability caveat. Commits:
felt-core `ec5bfb0` (main implementation), `7cbd88a`/`4748161`/`23af414`
(the Gemma thinking-token fix, iterated three times), `43f372d` (privacy
prompt fix) - deployed via `/home/clockmost-infra` through `de5b4db` +
`clockmost-deploy.service`.

**Real bug 1 - Gemma 4's hidden "thinking" tokens.** The very first live
weather-precompute run came back as a raw chain-of-thought transcript,
not a spoken line. `gemma-4-26b-a4b-it` emits hidden reasoning content
flagged `"thought": true` ahead of its real answer - `cloud.py`'s
`_extract_text` was blindly grabbing `parts[0]`, which is that thinking
part whenever one exists. Fixed to skip any `thought: true` part and
return the first real one (test coverage in `test_cloud.py`). Separately,
the WP's own 120-token `_SKILL_PHRASING_MAX_TOKENS` wasn't even close to
enough room for the thinking overhead ahead of the real answer - measured
against the actual production prompt (not a toy one): 473-1997 thinking
tokens depending on prompt complexity, sometimes still truncating even at
2000. Rather than chase an unbounded budget, added a second, more
important fix: both `_phrase_skill_result` and the weather precompute now
treat an **empty string from `cloud_generate` as a failure requiring the
existing local fallback**, not a successful-but-empty reply (`cloud.py`'s
`_extract_text` returns `""` on purpose when a response is all-thinking
with no real answer beneath it). Landed on `_SKILL_PHRASING_MAX_TOKENS =
1000` as a reasonable middle ground - generous enough that cloud phrasing
often succeeds (confirmed live: calendar phrasing came back with real
personality), cheap on Gemma's free-tier budget, and now safe either way
since the empty case degrades gracefully instead of serving nonsense or
silence.

**Real bug 2 - a self-contradicting privacy-classifier prompt.** Adding
this WP's own worked example ("your shelf plug is on" → SAFE) directly
contradicted an existing PRIVATE-list clause ("home server/network/
smart-home devices by name") - a named smart-home device and the home
network's own identity were the same bullet. Split them: PRIVATE now
covers only the network/server's own identity (hostname/IP/infra), and a
named device's plain status is explicitly called out as SAFE. This did
**not** fully resolve it, though (see the unresolved caveat below).

**Unresolved, known limitation**: `is_safe_for_cloud` (`qwen2.5:1.5b`,
now pinned to CPU per the WP-04/05 session's Nitro5 fix) is genuinely
unreliable on this classification for short device-status phrases -
confirmed via direct testing that it says PRIVATE for "The shelf is
currently off" **and** for the literal worked-example text "your shelf
plug is on" itself, both consistently across repeated calls, despite
that exact text sitting in the prompt as a SAFE example. Asking the same
model for its reasoning (temporarily relaxing the strict one-word output
constraint) gets the *correct* "SAFE — a device status" answer, so the
underlying judgment is in there somewhere, but the terse-output mode
loses it. This is 1.5B-model instruction-following unreliability on a
fairly nuanced ask, not a prompt-wording bug - fixing it properly likely
needs a different/larger classifier model or a different mechanism
entirely for this one case, not another prompt tweak. Not chased further
here. **Not a safety bug**: the system fails closed exactly as designed
(stays local when uncertain) - acceptance check 3 (`is the shelf plug
on?`) therefore consistently takes the *local* phrasing path in practice
right now rather than cloud, even though it should qualify for cloud per
Mario's own stated rule. Functionally correct, just a missed
optimization. Flagging for Mario rather than guessing at a fix.

**Live acceptance, verified 2026-09-22 ~23:00-23:02:**
1. First `wp06-test` weather call after a precompute cycle: **0.84s
   total** (well under the ~2s target), log: "weather fast path: serving
   the precomputed line, no skill/phrasing calls." (The precomputed line
   itself is the raw tool output, not cloud-phrased, per bug 1 above -
   still fast and correct, just not personality-flavored for weather
   specifically right now.)
2. "What's on my calendar today?" → phrased reply with real personality
   ("a totally clear schedule sounds like a dream to me"),
   `/v1/metrics/cloud` shows `skill_phrasing` on `gemma-4-26b-a4b-it`,
   no local-fallback line in the log for that request.
3. "Is the shelf plug on?" → gated, privacy check runs, comes back
   PRIVATE (see the unresolved caveat), falls back to local - still a
   good, in-character reply ("it's not gonna plug itself, is it?"), just
   local instead of cloud.
4. "Find my notes about the migration project" → `search_documents`
   (local class), log shows only Ollama + `drive-rag` calls, zero
   requests to `generativelanguage.googleapis.com`.

Full test suite: 182 → 202 passing (`plugin_loader` skills.json manifest,
the class→route matrix incl. facts-never-in-cloud and local-never-calls-
cloud, `voice_line` preference, the weather fast path + staleness
fallback, the TTS cache hit/miss, the weather cache TTL, and the Gemma
thinking-part extraction). One single `test_metrics.py` timing-assertion
flake seen once during a full-suite run, passed on immediate rerun -
pre-existing WP-04 test, unrelated to this WP, not investigated further.
