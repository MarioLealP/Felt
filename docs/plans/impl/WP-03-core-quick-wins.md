# WP-03 — felt-core quick wins: image-skill guard, parallel router/privacy, speech-style output

**Repo**: `E:\Felt\felt-core` (server, so deploy). **Size**: S. **Depends
on**: WP-02 (same files; avoids merge pain).

## Why

- **Misroute with side effects**: "tell me something fun about octopuses" was
  routed by the small router (`qwen2.5:1.5b`) to `generate_image`. That
  submitted a real ComfyUI job, polled it for ~48 s, and the whole turn took
  136 s. Measured 2026-09-22.
- **Serial small-model calls**: `chat()` runs the router, then (only if no
  skill was chosen) the privacy classifier, sequentially. Both are round trips
  to the Nitro5 (router ~3.8–4.9 s measured).
- **Replies are spoken but written like text**: nothing forbids markdown,
  lists or emoji, and nothing strips them before TTS. The measured weather
  reply was a long, rambly ~0.8 MB WAV, and TTS took 12 s of the 33 s turn.

## Changes

### 1. Guard `generate_image` (brain.py, after `decide_tool`)
Only accept a `generate_image` routing if the message has an explicit
make-intent. Otherwise treat it as `call = None` (plain chat):
```python
_IMAGE_INTENT_RE = re.compile(
    r"\b(draw|paint|sketch|generate|make|create|render|design)\b.*\b(image|picture|pic|drawing|painting|art|portrait|wallpaper|illustration)\b"
    r"|\b(draw|paint|sketch)\s+(me|us|a|an|the)\b",
    re.IGNORECASE,
)
```
Log at INFO when the guard overrides the router. Put it in a small table
`_SKILL_GUARDS: dict[str, Callable[[str], bool]]` so other expensive or
side-effect skills can get guards later.

### 2. Router and privacy check in parallel (`chat()`)
When `config.gemini_api_key` is set, start the privacy check as a task at
the same time as the router:
```python
privacy_task = asyncio.create_task(is_safe_for_cloud(_format_for_privacy_check(history, message), config)) if config.gemini_api_key else None
call = await decide_tool(message, registry, config)
```
- **No skill** → `_chat_reply` receives the already-running task's result
  (change its signature to take `safe: bool | None`, where `None` means not
  checked / no key).
- **A skill** → `privacy_task.cancel()` (swallow `CancelledError`).
- Keep the fail-closed semantics exactly: any exception means not safe.

### 3. Speech-style output
- Append to `_PERSONALITY_PROMPT`: "Everything you say is spoken aloud by a
  voice, never shown as text: no markdown, no lists, no emoji, no URLs; say
  numbers and units the way a person would out loud; lead with the answer."
- In the skill-result reply prompt (the `(Tool result: …)` block), add:
  "Answer in one or two short spoken sentences; then, only if it fits, one
  short bit of personality (an opinion, a suggestion)."
- Local path length cap: pass `"options": {"num_predict": 160}` in
  `_ollama_chat` for reply generation (add a `max_tokens` parameter; the
  router/privacy calls already have their own options).
- New `felt_core/speech.py` with `strip_for_tts(text) -> str`:
  - remove `**`, `__`, `*`, `_` used as emphasis, backticks, `#` headings,
    leading list markers (`- `, `* `, `1. `);
  - replace URLs with "a link";
  - drop emoji (Unicode ranges; keep accented letters);
  - collapse whitespace.

  Use it in `api._synthesize_reply` **only for the text sent to TTS**. The
  `X-Reply-Text` header keeps the original, for toasts and chat.

## Tests
- `test_router_guards.py`: the octopus message is rejected; "draw me a cat
  riding a motorcycle" and "generate an image of a red panda" are accepted.
- `test_brain_parallel.py`: with monkeypatched slow fakes (each sleeping
  0.3 s), a no-skill `chat()` takes ~0.3 s, not ~0.6 s. A skill path cancels
  the privacy task (assert it was cancelled). A privacy exception still
  means local.
- `test_speech.py`: markdown, lists, URL and emoji cases; accents preserved
  ("Olá, está 15°").
- The whole suite is green.

## Deploy + acceptance
Deploy, then with session `wp03-test`:
1. `POST /v1/chat {"message": "tell me something fun about octopuses"}`:
   the server log shows **no** `:8188` (ComfyUI) request, and the reply is a
   fun fact.
2. `POST /v1/chat {"message": "what's the weather like right now?"}`: the
   reply is ≤ 2–3 short sentences.
3. `POST /v1/chat {"message": "give me three tips for sleeping better"}`:
   `X-Reply-Text` (via `/v1/text-chat`) may contain a list, but the TTS input
   has no `-`/`*`/numbers-with-dots. Log the stripped text at DEBUG and
   check it.

## Notes from implementation (2026-09-22)

Implemented as specced. Commit: felt-core `8431900`, deployed via
`/home/clockmost-infra` `0bb5c37` + `clockmost-deploy.service` ("OK —
deployed felt-core").

- `_guard_generate_image` + `_SKILL_GUARDS` table in `brain.py`, checked
  in `chat()` right after `decide_tool` returns, before the
  skill-vs-no-skill branch (so an overridden call correctly falls into
  the no-skill path and the concurrently-running privacy task gets
  awaited rather than cancelled).
- `chat()` now creates the privacy-check task alongside `decide_tool`;
  `_chat_reply` takes the precomputed `safe: bool | None` instead of
  computing it itself. Fail-closed wrapped in `try/except Exception:
  safe = False` around `await privacy_task` in `chat()` itself, in
  addition to `is_safe_for_cloud`'s own internal catch - belt-and-
  suspenders in case the task raises directly rather than through that
  function's own try/except.
- `_ollama_chat` gained a `max_tokens` kwarg -> `options.num_predict`;
  `_REPLY_MAX_TOKENS = 160` used by `_local_reply` (all its callers are
  reply generation) and the tool-result reply call in `chat()`. Personality
  prompt and the tool-result prompt both got the "spoken aloud" framing.
  `felt_core/speech.py::strip_for_tts` wired into `api._synthesize_reply`,
  TTS input only - `X-Reply-Text` keeps the unstripped original.

Deviations / notes:
- The server-side deploy commit step (`git add && git commit` in
  `/home/clockmost-infra`) needed to be run manually this time - the
  auto-sync timer hadn't picked up the change yet at the moment I ran it
  (unlike WP-02, where it beat me to it). Both are valid depending on
  timing; the context doc's "you must push yourself" instruction holds.
- Acceptance check 3's live `/v1/text-chat` call happened to get a reply
  with no markdown in it at all (the personality prompt's own
  "no markdown/lists" instruction working as intended upstream) - nothing
  to observably strip from that particular reply. Verified `strip_for_tts`
  directly instead, exec'd against the actual deployed container
  (`docker compose exec felt-core python -c "..."`) with a realistic
  markdown+list+URL+emoji sample - confirmed it strips correctly against
  the real production code, not just the local unit tests.
- Full test suite: 149 -> 167 passing. One test
  (`test_skill_path_cancels_the_privacy_task`) was flaky on the first
  write - cancelling a freshly-created task before its coroutine has run
  its first step throws `CancelledError` in before that task's own
  `try/except` ever executes. Fixed by giving `decide_tool`'s fake a real
  `await asyncio.sleep(0)` so the concurrently-created privacy task
  actually gets scheduled first.
