# Felt

A local-first AI companion for Mario's desktop: text/voice chat backed by a
local model (with opt-in cloud delegation for banter it isn't great at), and
an animated VRM avatar that lives on the desktop and reacts to the
conversation - lipsync, expressions, idle behavior, the works.

This is the **umbrella repo**: top-level docs, design history
(`docs/plans/`), and the launcher scripts that boot the whole stack. Each
real component below is its own independently-versioned git repo, cloned as
a sibling folder here (not a submodule - see "Repo layout").

## Philosophy

Felt is built assuming it may eventually be public, and to be genuinely
usable by someone who isn't its original author. Two rules follow from
that, enforced project-wide:

1. **No hardcoding.** No IPs, hostnames, file paths, API keys, or other
   environment-specific values baked into code - everything goes through
   config (env vars / `.env`), documented per-service in each service's
   `.env.example`.
2. **Modular / plugin architecture.** Skills (weather, price checks, smart
   home, ...) are self-contained plugins implementing one small interface -
   addable/removable without touching core code.

And one consequence worth stating up front: **the local model is the
default brain; cloud is opt-in per call**, gated by a dedicated fail-closed
privacy classifier, never a default path for something local can already
handle.

## How a message actually flows

```
you (voice or typed text)
  -> felt-tray (push-to-talk / hotkey / chat window)
     or felt-dashboard (the chat UI felt-tray hosts)
  -> felt-core  [the brain]
       - routes tool-vs-chat (small dedicated classifier model)
       - plain chat: local model, or Gemini direct API if the privacy
         classifier clears it (never for tool-result replies - those can
         carry real personal data, so they always stay local)
       - skills: weather, calendar, email, smart home, PoE2 prices, ...
       - felt-voice: STT in, TTS out
  -> felt-tray plays the reply (toast + audio) and forwards the resolved
     animation_tag on to felt-animation
  -> felt-animation decides the actual reaction clip, generates lipsync
     cues (Rhubarb, fully local/offline), and drives felt-overlay over a
     small local TCP relay
  -> felt-overlay (felt-character-assets/felt-godot-overlay) is what you
     actually see: the VRM avatar animating, lipsyncing, and expressing on
     the desktop
```

`felt-animation` and `felt-overlay` are themselves fed by two offline
authoring pipelines: `AnimToVrmaConverter` (Mixamo animations → `.vrma`)
and `felt-t2a-studio` (text prompt → `.vrma`, using a T2M-GPT server on the
Nitro5 laptop) - both promote approved clips straight into
`felt-character-assets`'s curated animation library.

There's also a passive, non-conversational path: `felt-tray`'s desktop
watcher (a Win32 `EVENT_SYSTEM_FOREGROUND` hook - fires on window switch,
not continuous polling) grabs a screenshot, sends it to `felt-vision`
(a thin FastAPI wrapper around the desktop's local Ollama `llava` model)
for a plain-language description, and forwards that to felt-core's
`POST /v1/context/screen`. felt-core decides whether it's worth reacting
to out loud (interesting) or not (mundane, stays silent) and the reply -
if any - flows back through felt-tray to felt-animation exactly like any
other reply. `felt-vision` has to actually be running for any of this to
work - it's not auto-restarting/supervised beyond being started by Launch
Felt, so if it's ever killed directly, screen reactions silently stop
until the next Launch Felt (confirmed live, 2026-09-22 - this was the
whole reason reactions weren't happening at all for a while).

## Components

| Repo | Role | Runs | Status |
|---|---|---|---|
| [`felt-core`](https://git.clockmost.com/Benylin/felt-core) | The brain - routing, skills, conversation memory, cloud/local chat split | clockmost server | running |
| [`felt-voice`](https://git.clockmost.com/Benylin/felt-voice) | STT + TTS | Nitro5 laptop | running (not checked out locally on the desktop) |
| [`felt-tray`](https://git.clockmost.com/Benylin/felt-tray) | Desktop shell - tray icon, global hotkeys, push-to-talk, felt-overlay lifecycle + relay | this desktop | running |
| [`felt-dashboard`](https://git.clockmost.com/Benylin/felt-dashboard) | The chat UI (text + voice), hosted inside felt-tray's window | this desktop (built, hosted by felt-tray) | running |
| [`felt-animation`](https://git.clockmost.com/Benylin/felt-animation) | Behavior/reaction decisions, lipsync generation, owns the felt-overlay process | this desktop | running |
| [`felt-character-assets`](https://git.clockmost.com/Benylin/felt-character-assets) | The VRM avatar + `felt-godot-overlay` (the actual on-screen renderer) | this desktop | running |
| [`felt-t2a-studio`](https://git.clockmost.com/Benylin/felt-t2a-studio) | Text-prompt-to-animation authoring tool | this desktop (+ Nitro5 for inference) | working |
| [`AnimToVrmaConverter`](https://git.clockmost.com/Benylin/AnimToVrmaConverter) | Mixamo animation → `.vrma` conversion pipeline | this desktop (+ headless Unity) | working |
| [`felt-vision`](https://git.clockmost.com/Benylin/felt-vision) | VLM middleware for passive desktop-reaction screenshots (Ollama `llava`) | this desktop | running |

**Retired, from the pre-Windows-migration Linux setup, no longer part of
this project:** `felt-desktop-agent` (D-Bus/KDE-Connect glue, Linux-only)
and the Tauri (`src-tauri/`) dashboard shell - replaced by `felt-tray`'s
Python/pywebview shell after the desktop moved from Linux to Windows
(2026-09).

## Running it

Desktop shortcuts (created 2026-09-21):

- **Launch Felt** - starts everything: checks/starts local Ollama, then
  `felt-animation` (which also launches `felt-overlay`) and `felt-tray`.
- **Update Felt** - commits any new assets dropped into
  `felt-character-assets` (new `.vrma` clips, a swapped model), re-exports
  the Godot overlay, and restarts `felt-animation`. Run this after adding
  new animations - felt-overlay only plays clips baked in at export time.
- **Convert Animation** - drag a Mixamo `.anim`/`.unitypackage` file onto
  it to convert straight to `.vrma` (`AnimToVrmaConverter/anim2vrma.bat`).
- **Felt Folder** - opens `E:\Felt` in Explorer.
- **Start Nitro5** (added 2026-09-22) - starts `felt-voice` (STT/TTS) and
  `ollama` on the Nitro5 laptop if either isn't already running. Never
  touches ComfyUI - that's still Mario's manual hand-swap with Ollama for
  the Nitro5's 6GB VRAM budget, and this script only ever starts services,
  never stops or restarts anything.

From a terminal, the underlying scripts: `E:\Felt\LaunchFelt.ps1` /
`E:\Felt\UpdateFelt.ps1` / `E:\Felt\StartNitro5.ps1`.

## Repo layout

```
E:\Felt\
  README.md              <- this file
  LaunchFelt.ps1, UpdateFelt.ps1, godot_path.txt   <- tracked here (godot_path.txt is gitignored, machine-local)
  Launch Felt.bat, Update Felt.bat                 <- Desktop shortcuts point at these
  docs/plans/             <- design docs and task briefs, see below
  Animations/             <- shortcut into felt-character-assets's animation library (see below)
  Model/                  <- shortcut into felt-character-assets's characters/ folder (felt.vrm - the only one)
  felt-core/               \
  felt-animation/           |
  felt-tray/                 > each its own independent git clone,
  felt-dashboard/            | not a submodule of this repo
  felt-character-assets/    |
  felt-t2a-studio/          |
  AnimToVrmaConverter/      |
  felt-vision/              /
```

`F:\workspace\Projects\<repo>` is a directory junction pointing at each of
these - editing/git from either path hits the same files in real time, so
existing muscle memory pointed at the old workspace location still works.

**`Animations\` and `Model\` are also junctions** (into
`felt-character-assets\felt-godot-overlay\animations\library` and
`...\characters` respectively) - added 2026-09-21 so the actual animation
clips and the base VRM model are visible right here instead of buried four
folders deep. The real, git-tracked files live in `felt-character-assets`;
these are just direct shortcuts to them, so dropping a new `.vrma` into
`E:\Felt\Animations\<tag>\` or swapping `E:\Felt\Model\felt.vrm` is exactly
the same as doing it inside `felt-character-assets` itself - then run
**Update Felt** to bake it in. `characters/` only ever held one real model
(`felt.vrm`) as of 2026-09-21 - two abandoned reference models
(`chen_qianyu.vrm`, `vroid_test.vrm`, plus the ~330MB `chen_qianyu/`
conversion-experiment folder) were deleted, see
`felt-character-assets/README.md` for what and why.

## docs/plans

Design docs and the original task briefs written for delegated work on
this project - kept for the *why*, not day-to-day reference:

- `gemini-task-felt-animation.md` - the original felt-animation/felt-overlay
  behavior design brief.
- `gemini-task-felt-natural-animation.md` - the follow-up pass (blend
  timing, expressions, blinking, anti-repeat).
- `t2a-architecture-whitepaper.md`, `t2a-6gb-implementation-plan.md` - the
  text-to-animation (T2A) pipeline design, built around the Nitro5's 6GB
  VRAM budget.

Each component repo's own `README.md` is the source of truth for its
current state - these are history, not living docs.
