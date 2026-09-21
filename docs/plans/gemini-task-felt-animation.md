# Task: build `felt-animation` — Felt's local, desktop-side animation/behavior service

## Context: what Felt already is

Felt is Mario's AI desktop companion, a VRM character rendered by a
transparent, click-through, always-on-top Godot overlay
(`felt-character-assets/felt-godot-overlay/`, exported to
`build/windows/FeltOverlay.exe`). The existing pieces, all real, working,
and NOT what you need to build:

- **felt-core** (`felt-core/`) - the conversational brain. Runs on the
  home server (`http://192.168.1.110:8420`). `POST /v1/chat` and
  `POST /v1/voice-chat` take a message/audio in, return a reply (text, and
  for voice, TTS audio too) plus an optional `animation_tag` (currently
  only ever set when a skill/tool fires, e.g. a weather lookup - plain
  conversational replies get `animation_tag=null`). Read
  `felt-core/src/felt_core/api.py` and `brain.py` to see this exactly.
- **felt-tray** (`felt-tray/`) - the Windows desktop shell. Owns the
  system tray, global push-to-talk hotkey, mic capture, toast
  notifications, and (**today**, about to change - see below) launching
  felt-overlay and relaying animation tags to it. Read
  `felt-tray/src/felt_tray/app.py` and `overlay.py`.
- **felt-overlay** (`felt-character-assets/felt-godot-overlay/main.gd`) -
  **presentation-only, by firm existing design principle**. It knows its
  own curated animation library (`animations/library/<tag>/*.vrma`, folder
  nesting = tag, no manifest file) and a tiny local TCP listener
  (`_start_tag_listener()`/`_poll_tag_listener()` in `main.gd`) that reads
  newline-delimited JSON `{"tag": "..."}` and plays a random clip from
  that *exact* tag's bucket - no fallback/broadening logic, never has.
  **Do not add decision-making logic to main.gd.** Everything below is
  decided elsewhere and sent to felt-overlay as an already-resolved,
  concrete tag.

## Goal

A new project, `felt-animation` (create it at `F:\workspace\Projects\felt-animation\`,
its own git repo, pushed to `git@git.clockmost.com:Benylin/felt-animation.git`
- same SSH push-to-create pattern every other Felt repo uses, `main`
branch), that owns **all** of Felt's behavior and animation
decision-making: reacting to conversation, idling/wandering when nothing's
happening, and driving lipsync. It runs **entirely locally on the desktop**
- no cloud, no GPU dependency, nothing added to felt-core (felt-core stays
exactly as it is, doesn't even need to know felt-animation exists).

This entire plan was worked out conversationally with Mario tonight
(2026-09-21) - the design below reflects real decisions he made, not
things you need to re-derive or second-guess. Where something below says
"Mario decided X", that's settled; don't relitigate it.

## Architecture change: felt-animation absorbs felt-tray's overlay-relay role

Today, felt-tray both launches felt-overlay (`OverlayManager` in
`overlay.py`) and sends it animation tags after a voice-chat reply comes
back. **That role moves to felt-animation.** felt-tray narrows down to:
mic capture, hotkeys, toast, the chat window, and now, calling into
felt-animation's local API instead of talking to felt-overlay directly.
felt-animation becomes the sole owner of the felt-overlay process
(launch/kill) and the TCP tag relay (reusing the *exact* same wire
protocol already in `felt-tray/src/felt_tray/overlay.py`'s `send_tag()` -
don't change that protocol, felt-overlay's listener doesn't need to
change).

You will need to **modify felt-tray** to remove its overlay-owning code
and instead call felt-animation's new local API (see below) at the right
points. This is a real, in-scope part of this task, not a separate one.

## Core design decisions (all settled in conversation - build these, don't redesign them)

### 1. Reactive animation choice = tool-calling, via a small local LLM

felt-core's own router (`felt_core/router.py`, `decide_tool()`) already
does exactly this kind of small-model tool-calling classification (using
`qwen2.5:1.5b` via Ollama) for every single message, before the main
reply is generated - it decides tool-vs-chat and which tool. felt-animation
does the same *pattern*, but as its own separate local decision, with
`play_animation(tag: string)` as (one of) its callable tools, given the
reply text felt-core already produced as context.

- **Runs on Ollama, installed locally on the desktop** (not the same
  Ollama felt-core's router uses, which runs on the Nitro5 laptop over the
  network - felt-animation needs its own local instance so it has zero
  network dependency). Desktop GPU is AMD (RX 6700), not officially
  supported by Ollama on Windows - **start CPU-only** (Mario, 2026-09-21:
  confirmed fine, given this is short tool-call-style output, not long
  generation - should be well under a second even on CPU for a model this
  small). A ROCm workaround (`HSA_OVERRIDE_GFX_VERSION=10.3.0`) exists as
  a documented fallback if CPU turns out too slow in practice, but don't
  build that path unless CPU-only is actually measured as too slow.
- Same small model class as felt-core's router (`qwen2.5:1.5b` or similar)
  is the reasonable default - it's already proven to work for exactly this
  kind of tool-calling classification task in this codebase.
- The tool schema needs a `play_animation(tag)` tool whose valid tag
  values are drawn from felt-overlay's actual current library (scan
  `felt-godot-overlay/animations/library/` for the real tag list at
  startup, don't hardcode it - the library keeps growing).

### 2. One principle covers all animation transitions: never interrupt, always finish first

Mario, 2026-09-21, correcting an earlier "race the reply against a timer"
idea: **there is no race.** Whatever animation is currently playing/
committed to always finishes its natural course before any transition
happens - full stop, one rule, applied everywhere:

- **Idle → prompt arrives → thinking plays → reply arrives → reply
  animation.** The thinking animation always plays to completion; if the
  reply isn't ready yet when it finishes, hold/loop until it is, then
  transition. Never cut thinking short even if the reply is already ready.
- **Mid-ambient-behavior (walking/sitting) → prompt arrives → ambient
  action finishes naturally → idle (no thinking animation needed, she's
  already transitioning) → reply arrives → reply animation.** Don't
  interrupt ambient behavior for an incoming prompt; let it finish, THEN
  go idle and wait for the reply.

Practically: felt-animation needs to track "what's currently
playing and can it be interrupted right now" and defer any pending
transition until the current thing reaches a safe stopping point (for a
looping clip like idle/thinking, that's just "finish the current loop
iteration").

### 3. Ambient/idle behavior is NOT LLM-driven - a separate, cheap, simple system

There's no context to reason about for "should she wander right now" - no
message to interpret. This should be a simple timer + weighted-random
state machine (e.g. every few minutes, mostly "stay idle", occasionally
"walk somewhere", occasionally "sit down") with **zero model inference**.
Keep the LLM calls reserved for when there's actual conversational content
to react to.

### 4. Movement: bounded, single-screen roaming

Mario, 2026-09-21: "She roams the main widescreen for now, keep it to
bounds so she is always visible." Single screen (the primary monitor -
matches felt-overlay's existing `LIMIT_TO_PRIMARY_MONITOR_FOR_TESTING`
setup in `main.gd`, no multi-monitor logic needed), bounded so she's never
off-screen or clipped. "Not single-axis" (Mario) - real 2D+ freedom
(across the screen, not sliding along one fixed horizontal line), which
has a real implication for the camera: felt-overlay's camera is currently
a *tightly-cropped, fixed* orthogonal view locked to a static character
position (see `main.gd`'s `_build_scene()` camera setup, framed from a
one-time AABB measurement). For her to actually roam, either (a) the
camera needs to track/follow her within a larger world space, or (b) the
camera needs to span the whole screen and she's repositioned within that
fixed view. **This is real Godot-side work in felt-overlay** (not just
felt-animation) - felt-overlay stays presentation-only (it doesn't decide
*where* she goes, felt-animation does), but it does need new code to
actually move the character node and adjust/follow with the camera as
felt-animation tells it to. Extend the existing TCP protocol for this
(felt-animation sends position/movement commands the same way it sends
animation tags) rather than inventing a separate channel.

### 5. State-layered reactions: standing vs sitting variants

Tags get a state-qualifier subfolder: `<reaction>/standing/` and
`<reaction>/sitting/` (e.g. `gesture/talking/standing/`,
`gesture/talking/sitting/`). felt-animation knows her current base state
(standing/sitting - tracked as part of its own state machine, set by
ambient behavior or by this logic itself) and resolves "semantic reaction
+ current state" to the concrete tag path before sending it to
felt-overlay - felt-overlay never needs to know state exists, it just
plays whatever exact tag it's told, same as always.

**Fallback when no state-specific variant exists** (most of tonight's
library is standing-only right now, so this will be common at first):
Mario, 2026-09-21, "stand up then play, latency is fine" - if she's
sitting and the reaction only has a standing variant, play a stand-up
transition first, then the standing reaction. **This means a stand-up/
sit-to-stand transition clip is required content**, not optional - if
`felt-godot-overlay/animations/library/` doesn't have one yet, flag this
clearly rather than silently skipping the stand-up step (Mario will need
to grab one from Mixamo).

### 6. Local lipsync via Rhubarb Lip Sync

felt-core's voice-chat response already includes both the reply text
(`X-Reply-Text` header) and real TTS audio (the response body) - felt-tray
already receives both today (`felt_tray/api_client.py`'s
`VoiceChatResult`). Run the audio through **Rhubarb Lip Sync** (an
established, fully offline/local command-line tool built exactly for
this - search for it, it's a real public tool, not something to build
from scratch) **with the reply text passed as the dialogue hint** (Mario,
2026-09-21: confirmed this is available "for free" and improves both
speed and accuracy over audio-only recognition). Output is per-phoneme/
viseme timing - relay that to felt-overlay alongside the animation tag
(extend the TCP protocol) so it can drive VRM's standard mouth-shape
expression blend shapes (`aa`, `ih`, `ou`, `ee`, `oh` - VRM 1.0's own
spec already defines these, this isn't custom to Felt) in sync with
audio playback. **This is real Godot-side work in felt-overlay too** -
applying blend-shape weights over time isn't something main.gd does today.

## felt-animation's local API (for felt-tray to call into)

Follow the same pattern already proven working tonight for
`felt-t2a-spike/inference_server.py` (FastAPI + uvicorn, a small local
HTTP server) - felt-animation should expose something equivalent, e.g.:

- `POST /request_started` - felt-tray calls this the moment it sends a
  request to felt-core (before waiting for the response) - triggers the
  thinking animation to begin.
- `POST /reply_ready` `{text, animation_tag, audio_bytes}` - felt-tray
  calls this once felt-core's response actually arrives - triggers
  lipsync generation + the eventual reply animation, gated by rule #2
  above (only once whatever's currently playing finishes).

Design the exact request/response shapes yourself, this is just the shape
of the interaction - two calls, not one.

## Explicitly out of scope for this build

**Screen awareness** (reacting to on-screen content) is a real, separate,
much bigger future pillar (screen capture, some form of visual
understanding, privacy considerations) - discussed tonight as an exciting
long-term idea, explicitly not part of this build. Don't build toward it,
don't leave elaborate hooks for it - just don't make decisions here that
would obviously preclude it later (e.g. don't hardcode assumptions that
felt-animation's only inputs are ever conversational).

## Definition of done

- `felt-animation` exists as its own repo, pushed to Gitea, `uv`-managed
  Python project (matches every other Felt Python project's tooling).
- Running it: launches felt-overlay itself (absorbed from felt-tray),
  exposes the local API above, runs its own local Ollama-backed
  tool-calling loop for reactions, runs a separate ambient timer/state
  machine for idle wandering, generates lipsync via Rhubarb for voice
  replies.
- felt-tray is modified to no longer own felt-overlay directly - it calls
  felt-animation's API instead at the two signal points.
- felt-overlay (`main.gd`) is extended (still presentation-only - no new
  *decisions*, just new *capabilities* it's told to use) to: move the
  character within screen bounds when told to, and apply mouth-shape
  blend weights from lipsync timing data it's given.
- End-to-end proof, same bar as tonight's other work: actually run it -
  mic a real question at Felt, confirm thinking plays, reply plays once
  ready, mouth moves roughly in sync with the audio, and ambient
  wandering visibly happens when left alone for a few minutes.
