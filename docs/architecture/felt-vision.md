# felt-vision

## Purpose

FastAPI wrapper around Ollama's LLaVA vision model. Analyzes desktop screenshots with privacy-filtered descriptions (banks, email, documents → "viewing private content" instead of transcribing). Used as fallback by felt-tray when cloud unavailable.

## Runtime

- **Port:** 8080 (http://127.0.0.1:8080)
- **Launch:** LaunchFelt.ps1 (line 43-45) starts `.venv\Scripts\python.exe -c "from felt_vision.main import run; run()"`
- **Process:** Headless, hidden window, logging to `%TEMP%/felt-vision.log`
- **Dependencies:** Ollama running on 127.0.0.1:11434 (started by LaunchFelt.ps1's check at lines 1-24)

## Module Map

| File | LOC | Responsibility |
|------|-----|---|
| src/felt_vision/main.py | 75 | FastAPI app, /analyze endpoint, Ollama client, privacy prompt, logging |
| src/felt_vision/__init__.py | 2 | Package init |

## Interfaces

**Endpoint:** `POST /analyze`
- **Input:** multipart/form-data, image file
- **Output:** JSON `{"description": "..."}`
- **Error:** 503 if Ollama unreachable, 500 on processing error

**Config Sources:**
- `OLLAMA_URL` env var (default: "http://127.0.0.1:11434/api/generate")
- `VISION_MODEL` env var (default: "llava")

## Config

| Env Var | Default | Notes |
|---------|---------|-------|
| OLLAMA_URL | http://127.0.0.1:11434/api/generate | Hardcoded default, no .env.example |
| VISION_MODEL | llava | Comment suggests moondream, qwen2-vl testable |

No .env file or .env.example—all config via environment defaults.

## Tests

None. Relies on Ollama availability and assumes image format compatibility.

## Smells

- **Empty README** (E:\Felt\felt-vision\README.md) — no usage guide
- **No .env.example** — config discoverable only by reading main.py (lines 23-25)
- **Hardcoded exception handling** — connec timeout 30s fixed, no tuning
- **No logging on startup success** — only "starting up" logged; hard to verify readiness
- **Ollama dependency not documented** — implicit runtime assumption
- **Process matching in LaunchFelt.ps1** (line 27) kills by name/cmdline, not PID file

## Ranked Suggestions

1. **Add .env.example** (S, agent-ok) — document OLLAMA_URL, VISION_MODEL, suggest values
2. **Write README** (S, agent-ok) — explain purpose, setup, dependencies, privacy rules
3. **Add startup verification endpoint** (M, agent-ok) — GET /health that validates Ollama
4. **Tag log output** (S, agent-ok) — prefix lines with module name for clarity with felt-tray logs
5. **Test Ollama retry logic** (M, no) — backoff if Ollama slow to start; test with chaos
