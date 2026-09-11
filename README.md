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
| `felt-core` | `services/felt-core` (submodule) | **running** — brain, plugin system, router, 4 skills (`get_time`, `delegate_research`, `get_weather`, `remember_fact`), SQLite persistence (conversation + long-term facts), HTTP/WS API. Deployed on the clockmost server. |
| `felt-voice` | `services/felt-voice` (submodule) | **built** — STT (`faster-whisper`, CPU) + TTS (Piper), `POST /v1/tts` + `POST /v1/stt`, verified via a real HTTP round trip. Not yet deployed anywhere long-term; not yet wired to felt-core. |
| `felt-dashboard` | not created yet | planned — a plain website, wrapped for desktop use |
| `felt-automation` | not created yet | planned — ntfy, desktop-notification passthrough, KDE Connect |

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
