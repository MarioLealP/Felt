# Felt — system architecture map

Written for WP-38 (`docs/plans/felt-usefulness-plan-2026-09-26.md`, Track B /
Spike B1), synthesizing five per-repo `ARCHITECTURE.md` audits plus the
existing `docs/architecture/felt-vision.md`, `felt-voice.md` and
`umbrella-scripts.md` notes. This is the "where does everything live and how
does it talk to itself" reference — read a repo's own `ARCHITECTURE.md` (or
its section here) for module-level detail, and `ENGINEERING-RULES.md` for how
to change any of it.

Nothing below was verified live for this pass beyond what the five source
audits already verified (tests run, files read, endpoints cross-checked
against code). Treat anything not attributed to an audit as read-only
inference from those documents.

## 1. Machines

| Machine | OS / hardware | Role |
|---|---|---|
| **Desktop** (`CLOCKMOST`, `192.168.10.74`) | Windows 11 Pro, AMD RX 6700, 3440×1440 primary + 1920×1080 secondary at `x=3440,y=357` | Where Mario is. Runs the avatar overlay, the desktop shell, screen/input capture, and a desktop-local Ollama. Smart App Control (SAC) is on — see `ENGINEERING-RULES.md` §6. |
| **Nitro5 laptop** (`clockmost-nitro5`, `192.168.10.104`) | Linux, 6 GB VRAM GPU, login shell **fish** | The GPU node: voice (STT/TTS/RVC) and felt-core's own local-chat Ollama share this one card. Not production-grade — stopping/restarting services here for a batch job is fine (`00-implementer-context.md`). |
| **clockmost server** (`192.168.10.110`, `clockmost.com`) | AlmaLinux, Docker Compose, Caddy + Authentik SSO | Runs felt-core (the brain) plus sibling self-hosted services it calls (ntfy, Zabbix, drive-rag, poe2rag, Home Assistant, Gitea). Deploy is a **vendored-copy** flow, not a direct push (§3). |

## 2. Services → ports → launch

| Service | Host | Port | Launch |
|---|---|---|---|
| felt-core | clockmost server | `8420` (LAN only, no auth) | Docker container (`docker-compose.yml`), `restart: unless-stopped`. Deployed via a vendored copy + `clockmost-deploy.service`, **not** a push to this repo's own origin. |
| felt-animation | Desktop | `8421` HTTP; TCP **client** to `127.0.0.1:8765` | `LaunchFelt.ps1` → `.venv\Scripts\python.exe -m felt_animation` hidden. Owns and launches the overlay process. |
| felt-godot-overlay (`FeltOverlay.exe`) | Desktop | TCP **server** on `127.0.0.1:8765` | Spawned by felt-animation's `OverlayClient.launch()` (reuses an already-listening instance instead of double-launching — fixed 2026-09-26). Exported as a byte-identical-to-template exe + separate `.pck` (SAC constraint, §6). |
| felt-tray | Desktop | none of its own (serves felt-dashboard's `dist/` on an OS-assigned ephemeral port for its `pywebview` window only) | `LaunchFelt.ps1` → `python -m felt_tray` (never the `uv`-generated `.exe` shim — SAC blocks it on re-sync). |
| felt-vision | Desktop | `8080` | `LaunchFelt.ps1` → `python -c "from felt_vision.main import run; run()"`, hidden. Legacy vision fallback; **being superseded** (WP-06 review note). |
| felt-dashboard | (no process) | n/a | Built once (`pnpm build` → static `dist/`); felt-tray's `DashboardServer` serves it, `pywebview` points at it. Not run standalone in production. |
| Ollama (desktop) | Desktop | `127.0.0.1:11434` | Windows scheduled task `OllamaServe`, checked/started by `LaunchFelt.ps1` (10 s readiness loop). Used only by felt-animation's `reaction.py` (local tag classification) and `ollama_health.py`. |
| felt-voice | Nitro5 | `0.0.0.0:8421` — **same port number as felt-animation, different host**; don't conflate the two in logs/greps | `felt-voice.service` (systemd) → `uv run felt-voice-serve`. |
| Ollama (felt-core's) | Nitro5 | `11434` | `ollama.service` (systemd). Router model on CPU (`qwen2.5:1.5b`), local chat on GPU (`qwen2.5:3b`, `num_ctx=4096`). Models live on an NFS mount (`/mnt/clockmost-models`); a 2026-09-26 boot race left Ollama down ~2h until a `RequiresMountsFor` drop-in was added. |
| ComfyUI | Nitro5 | (internal) | Shared with the GPU above; used by felt-core's `generate_image` skill and the wardrobe/tee texture tooling. Sometimes stopped deliberately for a batch job (WP-19/33) — must be restored after. |
| Sibling server services felt-core calls | clockmost server | various | ntfy, Zabbix, drive-rag (RAG), poe2rag, Home Assistant OS VM (`ha.clockmost.com`) — see felt-core's own outbound-calls table. |
| Gitea board (WP-37) / Felt app (WP-42) | clockmost server | planned | Not built yet; referenced here because Track B/A outputs (this doc, the ranked list) are meant to become board tickets. |

## 3. Repos → machine → key modules

| Repo | Code lives at | Runs on | Detail |
|---|---|---|---|
| `felt-core` | `E:\Felt\felt-core` | clockmost server, Docker | [`felt-core/ARCHITECTURE.md`](../felt-core/ARCHITECTURE.md) — `brain.py` (orchestration, god file), `api.py` (all HTTP/WS routes), `cloud.py` (sole Gemini/Gemma choke point), `events.py` (event-reaction policy), `router.py`, `privacy.py`, `db.py` (12-table SQLite), `plugins/` (28 skills). |
| `felt-animation` | `E:\Felt\felt-animation` | Desktop, `:8421` | [`felt-animation/ARCHITECTURE.md`](../felt-animation/ARCHITECTURE.md) — `server.py` (god file: routes + most background loops), `props.py`, `overlay.py` (owns the overlay process + relay), `geometry.py`, `state.py`, `audio.py` (sole WAV playback owner since WP-08), `mood.py`, `lipsync.py`. |
| `felt-character-assets` | `E:\Felt\felt-character-assets` | Desktop (`FeltOverlay.exe`) | [`felt-character-assets/ARCHITECTURE.md`](../felt-character-assets/ARCHITECTURE.md) — `felt-godot-overlay/main.gd` (2868-line god file: scene build, face compositor, walk, relay, AnimationTree layers), `props/props.gd`, the VRM avatar and `.vrma` animation library. |
| `felt-tray` | `E:\Felt\felt-tray` | Desktop | [`felt-tray/ARCHITECTURE.md`](../felt-tray/ARCHITECTURE.md) — `app.py` (wires every collaborator), `capture.py` (blocklist-before-pixels policy + Win32 grab), `watcher.py`, `mic.py`, `hotkeys.py`, `tray.py`. |
| `felt-dashboard` | `E:\Felt\felt-dashboard` | Built static; served by felt-tray | [`felt-dashboard/ARCHITECTURE.md`](../felt-dashboard/ARCHITECTURE.md) — `App.tsx` (the whole app, one component), `lib/api.ts`, `lib/useMicRecorder.ts`. Candidate Track E app base (needs routing + a server-side felt-animation relay first). |
| `felt-vision` | `E:\Felt\felt-vision` | Desktop, `:8080` | [`docs/architecture/felt-vision.md`](architecture/felt-vision.md) — one file, `main.py` (75 LOC), a LLaVA-via-Ollama wrapper. No config file, no tests. |
| `felt-voice` | Nitro5, `~/felt-voice` (`ssh clockmost-nitro5`) | Nitro5, `:8421` | [`docs/architecture/felt-voice.md`](architecture/felt-voice.md) — `api.py`, `tts.py` (Chatterbox/Piper), `rvc.py` (Teto), `stt.py` (faster-whisper). |
| Umbrella (`E:\Felt` itself) | `E:\Felt\*.ps1`, `tools/` | Desktop (orchestration only, no process of its own) | [`docs/architecture/umbrella-scripts.md`](architecture/umbrella-scripts.md) — `LaunchFelt.ps1`, `UpdateFelt.ps1` (does its own `git add -A`, flagged), `StartNitro5.ps1`, asset tools (`tools/outfits`, `tools/sounds`). |
| `AnimToVrmaConverter` | `E:\Felt\AnimToVrmaConverter` | offline, run manually | Not covered by a WP-38 audit; holds the paid Movement Animset Pro conversions (never committed). |

`F:\workspace\Projects\<repo>` are junctions to these same files — same
content, different path, not a second copy.

## 4. Runtime data flow

### 4a. A voice reply (hotkey → she speaks)

```
Mario presses Ctrl+Alt+V
        │
        ▼
felt-tray (mic.py records) ──POST /v1/voice-chat──▶ felt-core (clockmost server)
                                                        │  router.py: tool vs chat?
                                                        │  privacy.py: cloud-safe?
                                                        │  brain.py: local Ollama (Nitro5)
                                                        │         or cloud (Gemini/Gemma via cloud.py)
                                                        │  reply text ──▶ felt-voice /v1/tts (Nitro5)
                                                        │                  Chatterbox/Piper → RVC (Teto)
                                                        ◀── WAV + X-Reply-Text / X-Animation-Tag headers
        ◀── WAV + headers ──────────────────────────────┘
        │
        ▼
felt-tray ──POST /reply_ready (text, tag, audio)──▶ felt-animation (desktop :8421)
                                                        │  audio.py: plays the WAV (sole owner since WP-08)
                                                        │  lipsync.py: Rhubarb → viseme cues
                                                        │  picks a reaction pose/tag
                                                        ▼
                                            TCP JSON, 127.0.0.1:8765 ──▶ felt-godot-overlay (main.gd)
                                                        plays clip, drives mouth, updates pose
```

### 4b. A screen reaction (window switch → she comments)

```
Mario switches windows
        │
        ▼
felt-tray watcher.py: enumerate_windows() → get_foreground_hwnd()
        │
        ▼
capture.py: decide_target() = exclusion_reason() or block_reason()   ◀── capture_blocklist.toml
        │  (metadata only — no pixels touched yet; if blocked, stop here)
        ▼ (only if a target survives)
capture.py: capture_window() — first line that touches real pixels
        │
        ├──POST /v1/context/screen──▶ felt-core (store observation)
        └──POST /v1/react/screen───▶ felt-core
                                        │  privacy.py: is_safe_for_cloud()?
                                        │  vision description: felt-vision /analyze (local llava)
                                        │         or Gemma multimodal, per WP-07
                                        │  brain.py: process_screen_context / react_to_screen
                                        │  reply text ──▶ felt-voice /v1/tts (Nitro5) ──▶ Teto WAV
        ◀── WAV + headers ─────────────────────┘
        │
        ▼
felt-tray ──POST /reply_ready──▶ felt-animation ──TCP 8765──▶ overlay
        (same tail as 4a)
```

### 4c. An ambient remark (music / presence / signal — no screenshot involved)

```
felt-animation background loop fires
  (music_loop, signals_loop [AFK/game/GPU/mash/call-energy], weather_loop, …)
        │
        ▼
POST /v1/react/event {event, details, tone?} ──▶ felt-core (clockmost server)
                                                    │  events.py: cooldown/dedupe policy table
                                                    │  (never stored as a screen observation)
                                                    │  reply text ──▶ felt-voice /v1/tts ──▶ Teto WAV
        ◀── WAV + X-Reply-Text / X-Animation-Tag ───┘   (skip reason comes back as X-Reaction-Skipped)
        │
        ▼
felt-animation: audio.py plays it directly (no felt-tray hop — this loop
lives inside felt-animation's own process), lipsync.py runs Rhubarb,
TCP 8765 ──▶ overlay plays the tag / lipsync / pose
```

Felt-tray is the entry point only for hotkey-driven voice and screen-watch
paths (4a/4b); felt-animation's own background loops (4c) talk to felt-core
directly and never route back through felt-tray.

## 5. Config and secrets

Every repo takes settings from its own `config.py` (or `config.ts` for the
dashboard) plus a matching `.env.example` — see `ENGINEERING-RULES.md` §2 for
the rule this enforces. Current state per repo (from the five audits):

| Repo | Config file | `.env.example` in sync? |
|---|---|---|
| felt-core | `config.py` (`FeltConfig`, pydantic-settings, `FELT_` prefix) | **No** — missing `FELT_GEMINI_API_KEY` (the actual cloud-enable switch) and the whole Home Assistant / HP-printer block. |
| felt-animation | `config.py` (`Config` dataclass, required paths raise at startup) | Yes, checked 1:1 — except `wardrobe.py`'s three hardcoded `E:/Felt/...` paths, which are outside the discipline entirely. |
| felt-tray | `config.py` (`.env`-backed dataclass) | Mostly — `FELT_VISION_URL` is read (hardcoded fallback `127.0.0.1:8080`) but missing from `.env.example`. |
| felt-dashboard | `src/lib/config.ts` (`VITE_*`) | Yes, both keys used and documented — the smallest, cleanest surface of the six. |
| felt-vision | none | **No `.env`/`.env.example` at all** — `OLLAMA_URL`/`VISION_MODEL` are env-var defaults discoverable only by reading `main.py`. |
| felt-voice | `config.py` (`VoiceConfig`, `FELT_VOICE_` prefix) | Yes — flagged smells are hardcoded *relative* paths (`./models/...`), not missing keys. |
| umbrella scripts | none | All paths hardcoded absolute in the `.ps1` files; no env file at all. |

Secrets live in **clockmost-infra's sops `secrets.env`** on the server (not
read for any audit) — by key name: `FELT_GEMINI_API_KEY`,
`FELT_GOOGLE_CALENDAR_CLIENT_SECRET`/`_REFRESH_TOKEN`,
`FELT_SPOTIFY_CLIENT_SECRET`/`_REFRESH_TOKEN`, `FELT_ZABBIX_API_TOKEN`,
`FELT_OCTOPRINT_API_KEY`, `FELT_IMAP_PASSWORD`, `FELT_NTFY_PASSWORD`/
`_PUBLISH_PASSWORD`, `FELT_NINEROUTER_API_KEY`, `FELT_HA_TOKEN`. Desktop and
Nitro5 have no secrets of comparable sensitivity today — the Nitro5's `.env`
holds only local tuning values.

## 6. Where state lives

| What | Where | Owner |
|---|---|---|
| Messages, alarms, facts, settings, shopping list, screen observations, cloud usage, music taste, event reactions, latency (12 tables) | One SQLite file at `FELT_DB_PATH`, on the `felt-data` Docker volume | felt-core, `db.py`, one `_connect()` for all schemas (no migration structure) |
| Per-track lyric cache | Flat JSON files, one per track | felt-core, `lyrics_client.py` |
| PoE2 trade reference data | One JSON file, weekly refresh | felt-core, `poe_trade_cache.py` |
| TTS render cache | In-memory LRU only, not persisted | felt-core, `tts_cache.py` |
| Mood vector | `%APPDATA%\Felt\mood.json` | felt-animation, `mood.py` |
| Placed-prop positions | `%APPDATA%\Felt\props.json` — **same filename, different purpose** than the repo-root `props.json` prop-definition manifest; a confirmed smell (§ ranked list) | felt-animation, `props.py` |
| Wardrobe rotation state | `E:\Felt\felt-animation\wardrobe.json`, `E:\Felt\Assets\tees\tees_approved.json` — hardcoded absolute paths, not under `%APPDATA%`, not in `.env` | felt-animation, `wardrobe.py` |
| Capture blocklist | `capture_blocklist.toml` (repo root, path overridable via `FELT_CAPTURE_BLOCKLIST`) | felt-tray, `capture.py` |
| Hotkey bindings | Rewritten in-place into felt-tray's own `.env` (`config.set_hotkey`) | felt-tray, `config.py` |
| Theme choice | Browser `localStorage` (per-viewer only) | felt-dashboard, `useTheme.ts` |
| Chat history | Not cached client-side — re-fetched from felt-core's SQLite on every mount | felt-dashboard |
| Godot user's exe path | `E:\Felt\godot_path.txt` | umbrella, `UpdateFelt.ps1` |
| Animation/prop/sound manifests | Versioned JSON/TOML at repo root (`props.json`, `sounds.json`, `reactions.json`, `games.toml`, `face_poses.json`) | felt-animation, read at startup |
| Voice model weights/cache | HuggingFace cache, `HF_HUB_OFFLINE=1` | felt-voice, Nitro5 |

## 7. Cross-repo contracts with no single source of truth

These are called out repeatedly across the five audits as the same class of
risk — a value hand-copied into two or more repos, kept in sync by comment
convention only:

- **`SESSION_ID = "dashboard"`** — felt-tray's `api_client.py` and
  felt-dashboard's `App.tsx` each hardcode the identical literal.
- **Tag-prefix classification** — `main.gd`'s `UPPER_TAG_CLASSES`/
  `BASE_TAG_PREFIXES`/`FULL_BODY_OVERRIDE_TAGS`, felt-animation's
  `overlay.py::is_looping_tag`, and felt-animation's `gaze.py::
  DEFAULT_OPT_OUT_TAGS` are three independently hand-synced lists across two
  repos.
- **Cursor/virtual-desktop geometry** — felt-animation's `cursor.py` and
  `geometry.py` each compute the monitor span independently.
- **OAuth token-cache pattern** — felt-core's `spotify_client.py` and
  `google_calendar.py` duplicate the same `_get_access_token()` shape.

`ENGINEERING-RULES.md` §3 turns "no more of these" into a checkable rule.

## 8. Repo ARCHITECTURE.md index

| Repo | Doc |
|---|---|
| felt-core | `E:\Felt\felt-core\ARCHITECTURE.md` |
| felt-animation | `E:\Felt\felt-animation\ARCHITECTURE.md` |
| felt-character-assets | `E:\Felt\felt-character-assets\ARCHITECTURE.md` |
| felt-tray | `E:\Felt\felt-tray\ARCHITECTURE.md` |
| felt-dashboard | `E:\Felt\felt-dashboard\ARCHITECTURE.md` |
| felt-vision | `E:\Felt\docs\architecture\felt-vision.md` (no per-repo file; smallest repo, one module) |
| felt-voice | `E:\Felt\docs\architecture\felt-voice.md` (lives on the Nitro5, not this umbrella's `git ls-files`) |
| umbrella scripts/tools | `E:\Felt\docs\architecture\umbrella-scripts.md` |

See `E:\Felt\docs\plans\impl\WP-38-architecture-audit.md` for the ranked,
merged refactor list drawn from all eight documents above.
