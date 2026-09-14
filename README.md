# Felt

A local-first AI assistant — an orchestrator ("brain") that routes between
a local model and on-demand cloud delegation, a growing set of pluggable
skills, a voice pipeline, a dashboard, and (eventually) a rigged 2D puppet
it can drive in real time.

This is the **umbrella repo**: architecture, cross-service docs, and git
submodules pointing at each independently-deployable service. Felt is
built as microservices deliberately — several pieces (voice, the
dashboard, home-automation glue) naturally run on different machines
(a GPU box, a desktop, a home server), so the repo structure reflects that
rather than fighting it with one monolith.

## Philosophy

Felt assumes it may eventually be public and usable by someone who isn't
its original author. Every service in this repo follows the same two
rules:

1. **No hardcoding.** No IPs, hostnames, file paths, API keys, or other
   environment-specific values in code — everything goes through config
   (env vars / `.env`), documented per-service in each service's
   `.env.example`.
2. **Modular / plugin architecture.** Skills/integrations are self-
   contained, addable/removable without touching core code.

And one architectural consequence worth stating up front: **the local
model is the default brain; cloud is opt-in per call**, never a default
path for something local can already handle.

## Services

| Service | Repo | Status |
|---|---|---|
| `felt-core` | `services/felt-core` (submodule) | **running** — brain, plugin system, deterministic router (temperature 0 + worked examples + JSON repair for tool disambiguation), 24 skills (`get_time`, `delegate_research`, `web_search`, `get_weather`, `remember_fact`, `get_recent_alerts`, `poe_price_check`, `set_timer`, `set_alarm`, `list_alarms`, `cancel_alarm`, `get_phone_battery`, `find_phone`, `printer_status`, `news_digest`, `get_gpu_status`, `get_container_status`, `media_control`, `check_email`, `generate_image`, `shopping_list`, `smart_home_control`, `list_calendar_events`, `create_calendar_event`), SQLite persistence (conversation + long-term facts), a proactive IMAP email watcher (needs real credentials in `.env` to run), image generation via the Nitro5's ComfyUI (verified live), ntfy subscribe (read) + publish (push, dedicated credential), HTTP/WS API, CORS-enabled and LAN-reachable, a real pytest suite + CI. Deployed on the clockmost server. |
| `felt-voice` | `services/felt-voice` (submodule) | **running** — STT + TTS, systemd service on the Nitro5, wired into felt-core via `/v1/voice-chat`, with a pytest suite covering caching + text handling. |
| `felt-desktop-agent` | `services/felt-desktop-agent` (submodule) | **running** — D-Bus notification passthrough (fullscreen/game-focus gated, native + KDE-Connect-relay filtering) + a small HTTP API for KDE Connect (battery, ring) and MPRIS media transport control (play/pause/skip/volume via `playerctl`), all as a `systemctl --user` service on the desktop, with a pytest suite + CI. |
| `felt-dashboard` | `services/felt-dashboard` (submodule) | **running** — the actual way to use Felt: text + voice chat UI, React/Vite/Tailwind on the Endfield tokens (forked from `clockmost-frontend-template`). Two ways to run it: a browser-tab production build served via a `systemctl --user` service (`felt-dashboard.service`), and a native Tauri app (`src-tauri/`) that lives in the system tray with a global keybind to show/hide, real native mic capture (cpal, bypassing a WebKitGTK MediaRecorder bug), and its own `systemctl --user` service (`felt-tray.service`). |
| KDE Connect SMS/calls | not built yet | planned extension of `felt-desktop-agent`'s existing KDE Connect API — deliberately deferred, sending a real message on Mario's behalf needs its own discussion first |

Each gets its own submodule + row here once it's actually scaffolded —
this table is the map, not a promise of what exists yet.

## Working with submodules

```
git clone --recurse-submodules git@git.clockmost.com:Benylin/Felt.git
# or, if already cloned:
git submodule update --init --recursive
```

Each service is developed and versioned independently (its own commits,
its own `.env.example`); this repo just pins which commit of each is the
current "known good" combination.
