# WP-05 — felt-core: cloud model split (Gemma 4 / Flash Lite) + quota governor

**Repo**: `E:\Felt\felt-core` (server, so deploy). **Size**: M. **Depends
on**: WP-04 (uses `timed()`).

## Why

Everything cloud-side runs on Mario's **free-tier** Gemini API. From his AI
Studio dashboard (2026-09-22; limits are **per model, per project**; daily
reset at **midnight Pacific**; there's **no remaining-quota header**):

| Model | RPM | TPM | RPD | Use |
|---|---|---|---|---|
| Gemma 4 26B (A4B MoE), multimodal | 30 | 16K | **14.4K** | volume: vision reactions, routing, public-skill phrasing |
| Gemma 4 31B, multimodal | 30 | 16K | 14.4K | A/B against 26B for quality |
| Gemini 3.5 Flash Lite | 15 | 250K | 500 | conversation |
| Gemini 3.1 Flash Lite | 15 | 250K | 500 | overflow for conversation |

WP-06 and WP-07 add many more cloud calls, so there has to be one choke point
that routes by *purpose*, counts calls, respects the limits, and falls back to
local.

## Changes

### 1. Find the real model ids first
List them:
`curl "https://generativelanguage.googleapis.com/v1beta/models?key=$KEY&pageSize=1000"`
(run it on the server with the key from the felt-core container env; **don't
print the key**). Record the exact ids for Gemma 4 26B/31B and 3.5/3.1 Flash
Lite in this WP's notes. The current setting is
`gemini_chat_model = "gemini-flash-lite-latest"`.

### 2. Config (`config.py` + `.env.example`)
```
cloud_model_conversation: str   # 3.5 Flash Lite id
cloud_model_overflow: str       # 3.1 Flash Lite id
cloud_model_volume: str         # Gemma 4 26B id
cloud_limits: str = ""          # optional JSON override: {"<model>": {"rpm": 15, "rpd": 500, "tpm": 250000}}
```
Built-in defaults: the table above. Keep `gemini_chat_model` working as an
alias for `cloud_model_conversation` (and read it if set), so the server's
existing secrets/env don't break.

### 3. `felt_core/cloud.py`: the single choke point
```python
class CloudUnavailable(Exception): ...

async def cloud_generate(
    purpose: Literal["conversation", "screen_reaction", "routing", "skill_phrasing", "summary"],
    system: str,
    messages: list[dict],               # [{"role": "user"|"assistant", "content": str}]
    images: list[bytes] | None = None,  # JPEG bytes
    json_mode: bool = False,
    max_tokens: int | None = None,
) -> str
```
- **Purpose → model**:
  - `screen_reaction`, `routing`, `skill_phrasing` → volume (Gemma)
  - `conversation`, `summary` → conversation, falling back to overflow
  - if the volume model is exhausted → overflow
- **Transport**: use the native REST `models/{id}:generateContent`, not the
  OpenAI-compatible endpoint, because images go in as `inline_data`
  (base64 JPEG).
  - `systemInstruction` for the system text.
  - **Gotcha**: Gemma models on the Gemini API have historically rejected
    `systemInstruction` ("developer instruction not enabled"). If the call
    400s for that reason, retry once with the system text prepended to the
    first user turn, and remember that per model for the process lifetime.
  - `json_mode` → `generationConfig.responseMimeType = "application/json"`.
    If Gemma rejects that, instruct "respond with only a JSON object" and
    parse leniently: extract the first `{…}`.
- **Governor** (a SQLite table `cloud_usage(model, purpose, pt_day,
  count)`, plus an in-memory sliding 60 s window per model):
  - `pt_day` = today's date in `America/Los_Angeles` (use `zoneinfo`).
  - Before a call: if the model's RPD would be exceeded (keep a 5 % safety
    margin), or its RPM window is full, try the purpose's fallback model; if
    none fits, raise `CloudUnavailable`.
  - Per-purpose soft caps on the volume model: `screen_reaction` ≤ 60 % of
    its RPD, so reactions can't starve routing or phrasing.
  - On HTTP **429**: mark that model exhausted until the next Pacific midnight
    (RPD) or for 60 s (RPM; decide from the error body if possible, else
    assume RPM), then try the fallback.
  - Estimate tokens (chars/4 + ~1,000 per image) and respect TPM (Gemma's
    16K/min matters for images).
  - Everything goes through `timed("cloud", model=…, purpose=…)`.
- `GET /v1/metrics/cloud` returns today's counts per model/purpose, the
  limits, exhausted-until timestamps, and the next reset time.

### 4. Migrate existing call sites
- `brain._cloud_chat` → `cloud_generate("conversation", …)`.
- `process_screen_context`'s cloud path → `cloud_generate("screen_reaction", …)`.
- Callers catch `CloudUnavailable` and use the existing local path. No
  behaviour change except model choice and counting.
- Delete the now-dead OpenAI-compatible request code.

## Tests
`test_cloud.py`, with httpx monkeypatched to fake responses:
- purpose→model routing;
- RPD exhaustion → fallback → `CloudUnavailable`;
- 429 marks the model exhausted until the Pacific midnight (freeze time);
- the systemInstruction-rejected retry path;
- image payload shape (`inline_data` with base64);
- the Pacific-day rollover.

Existing brain tests still pass.

## Deploy + acceptance
1. Deploy. `GET /v1/metrics/cloud` shows the configured models and 0 counts
   (or today's).
2. One `/v1/chat` banter message (session `wp05-test`) →
   `conversation` count +1 on the 3.5 Flash Lite id.
3. One screen-context call → `screen_reaction` +1 on the Gemma id, and she
   still sounds in character. If Gemma's persona quality is clearly worse,
   note it here for Mario rather than switching models silently.
4. Temporarily set `cloud_limits` to `rpd: 1` for the volume model on the
   server, make two screen calls, and confirm the second falls back
   (overflow or local) and the log says why. Then revert.
