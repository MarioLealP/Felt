# WP-02 — felt-core: screen observations out of chat history, privacy gap, always-spoken screen reactions

**Repo**: `E:\Felt\felt-core` (runs on the server, so deploy per the context
doc). **Size**: M. **Depends on**: none.

## Why (three real bugs plus one of Mario's decisions)

1. **Observations wipe her memory.** `brain.process_screen_context` saves
   every screen description as a `user` message
   (`[System Observation: …]`) into the same session as chat. The felt-tray
   and dashboard session id is `"dashboard"`. `db.get_history` returns only
   the last 20 messages, so ~20 window switches push the whole real
   conversation out of context. They also show up as fake "Mario said" bubbles
   in the chat window (`/v1/history` → `felt-dashboard/src/App.tsx`).
2. **Privacy gap.** `_chat_reply` checks the whole recent window (history +
   message) before going to the cloud. `process_screen_context` checks only
   the description, yet `_cloud_chat(prompt, history, …)` sends the last 6
   history messages. A conversation deliberately kept local can leak to
   Google alongside a harmless screen description.
3. **Silence by model.** The prompt lets the model answer `NONE`. On the cloud
   path Gemini said NONE 11 times out of 11, so she effectively never reacts
   aloud.
4. **Mario's rule:** screen reactions are always spoken. Frequency is
   limited by deterministic rules, never by the model.

## Changes

### 1. New table + helpers (`db.py`)
In `_connect`, add (same `CREATE TABLE IF NOT EXISTS` pattern as the others):
```sql
CREATE TABLE IF NOT EXISTS screen_observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  description TEXT NOT NULL,
  spoken_reply TEXT,              -- NULL when no reaction was spoken
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```
Helpers: `save_observation(db_path, session_id, description) -> int`,
`set_observation_reply(db_path, obs_id, reply)`,
`get_recent_observations(db_path, session_id, limit=3) -> list[dict]`
(chronological, with `created_at`), and
`seconds_since_last_spoken_reaction(db_path, session_id) -> float | None`.

### 2. Hide legacy observation rows (non-destructive)
`get_history` must exclude rows whose content starts with
`[System Observation` (`AND content NOT LIKE '[System Observation%'`).
That fixes both the brain's context and `/v1/history` for rows already in
the prod DB, **without deleting anything**. A one-off DELETE of those rows
is optional and needs Mario's explicit OK. Don't do it in this WP.

### 3. Rewrite `brain.process_screen_context`
- `obs_id = save_observation(...)`. **Never** `save_message` the
  observation.
- **Cooldown**: new config `screen_reaction_cooldown_s: int = 90`
  (`FELT_SCREEN_REACTION_COOLDOWN_S`, add to `config.py` and
  `.env.example`). If the last *spoken* reaction was less than the cooldown
  ago, return `ChatResult(reply="")` without calling any model. This is the
  deterministic frequency limit, and it stays even though the model no longer
  decides silence.
- **Prompt (no NONE option)**: "You just glanced at Mario's screen. Say ONE
  short, natural spoken remark about it (max ~15 words), in character. Never
  say you're looking at a screen or describe it neutrally. React like a friend
  sitting next to him." Include a system block `Recently on screen (oldest
  first):` with the last 3 observations, so she can notice continuity ("still
  on that boss?").
- **Cloud path**: send **no chat history at all**. Only personality + the
  observations block + the prompt. Keep the existing
  `is_safe_for_cloud(description)` check on the description.
- **Local path** (no key / not safe / cloud error): personality +
  observations + the **last 4 real chat messages** + prompt. Facts are not
  needed; don't include them.
- **Parsing**: strip whitespace and quotes. If the result is empty or equals
  `NONE` (a legacy habit), retry once on the local path. If it's still empty,
  log a WARNING and return an empty reply. Never silently eat a normal reply.
- On a spoken reply: `set_observation_reply(obs_id, reply)` **and**
  `save_message(session_id, "assistant", reply)`. She did say it, so it
  belongs in chat history as her line. The observation itself doesn't.

### 4. Normal chat gets "what's on screen now"
In `chat()`, if the most recent observation for the session is under
**120 s** old, add a system message `Currently on Mario's screen:
<description>` to the context. This is allowed on both local and cloud
paths: the description is the already privacy-filtered artifact. "What do
you think of this?" then works.

### 5. Cleanups on the same path
- Move the inline `from felt_core.brain import process_screen_context` in
  `api.py` to a top-level import.
- Factor the thrice-repeated local call
  (`_ollama_chat([personality] + facts + history + [user])`) into one helper
  `_local_reply(messages_tail, *, include_facts: bool)` and use it
  everywhere.

## Tests (`tests/`)
- `test_db_observations.py`: save/get/order/limit, spoken-reply tracking,
  seconds-since.
- `test_db_history.py` (extend): legacy `[System Observation…` rows are
  excluded.
- `test_brain_screen_context.py`: monkeypatch `_cloud_chat`, `_ollama_chat`
  and `is_safe_for_cloud`:
  - the cloud path receives **no** chat-history messages (assert on the
    `history` argument it got);
  - a NONE reply triggers exactly one local retry;
  - a second call inside the cooldown makes zero model calls;
  - a spoken reply is saved as an assistant message and the observation is
    not saved as a message.
- The whole suite stays green: `uv run pytest -q`.

## Deploy + acceptance

Deploy per `00-implementer-context.md`, then:

1. `curl -s -D - -o NUL -X POST http://192.168.1.110:8420/v1/context/screen?session_id=wp02-test -H "content-type: application/json" -d "{\"description\": \"A person is browsing a spreadsheet of monthly expenses.\"}"`
   returns `200` with an `X-Reply-Text` header (spoken) and a non-empty WAV
   body.
2. Repeat within 90 s: `200` with an empty body (cooldown). The server log
   shows no Ollama or Gemini call for that request.
3. `curl http://192.168.1.110:8420/v1/history?session_id=dashboard` contains
   no `[System Observation` entries.
4. Use a throwaway session id for tests (`wp02-test`), never `dashboard`.

## Out of scope

Image input (WP-07), budget governor (WP-05), deleting the legacy rows.
