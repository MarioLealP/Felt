# Delegating WPs to Gemini (Antigravity) or OpenHands

For **non-Claude agents** picking up a work package. Everything in
`00-implementer-context.md` applies too. Read it first.

## Who should take what

| WP | Best fit | Why |
|---|---|---|
| **WP-32** accessories/assets sourcing + Blender prep | **Antigravity (local)** | Bulk web search, downloads, headless Blender scripting. Grind, not design. |
| **WP-33** daily tee (texture generation, gallery, daily pick) | **Antigravity (local)** | Mostly image generation/compositing batches plus a small amount of code. It needs this PC (Godot renders) and the Nitro5 (ComfyUI). |
| WP-18 parts A+B (Animset Pro triage, downloads + conversions) | Antigravity (local) | Sorting, downloading and converting assets. |
| WP-19 steps 1–4 (Orpheus generation, RVC batch, curation page) | Antigravity (local) | Batch generation. The playback hookup (step 5) → Claude/Sonnet. |
| WP-24 hygiene | Antigravity or Sonnet | Mechanical. |
| Everything else (felt-core logic, state machines, protocol, main.gd systems) | Claude / Sonnet | Design-sensitive code where earlier "fully wired" claims went wrong. |

**OpenHands** runs on the server (see `F:\workspace\runbooks\ai-stack.md`)
and has no access to this desktop, the E: drive, Godot or the overlay. It only
suits pure felt-core server work with no desktop verification step, and even
then, deployment goes through the clockmost-infra flow in the context doc.

## Rules (these exist because of real past failures)

On 2026-09-22 a Gemini session reported the desktop-reactions feature as
"fully wired". It was never deployed, and its animation tags didn't exist, so
nothing worked. Mario: "it's a lie tho". So:

1. **No claim without evidence.** Every "done" item needs proof in the WP's
   "Notes from implementation" section, under a heading `### Proof`:
   - **Files**: the paths created or changed, with counts (e.g. "63 PNGs in
     `E:\Felt\Assets\tees\`").
   - **Commands**: the exact command and the relevant **raw output lines**
     (test results, HTTP status codes, log lines), pasted, not paraphrased.
   - **Visuals**: paths to screenshots or renders that show the result (for
     WP-32/33: the front renders and the gallery page path).
2. **Say what you did NOT do or couldn't verify**, explicitly, in a
   `### Not done / unverified` list. An honest gap is fine; a hidden one isn't.
3. **Stay inside your WP.** Don't edit files another WP owns. Don't "fix"
   unrelated things. If something outside the WP is broken, note it.
4. **Never tick a WP in `README.md` yourself.** Set its status to
   `🔎 needs review`. Claude (or Mario) verifies the proof and ticks it.
5. **Nothing leaves the privacy rules**: the capture blocklist, no secrets
   in files or logs, no paid assets (`Movement Animset Pro*.unitypackage`) in
   git.
6. **The Nitro5**: you may stop Ollama/ComfyUI there for a batch. **Restore
   whatever was running before** and note it. Its shell is fish, so wrap bash
   in `bash -c '…'`.
7. **Commit so it can be rolled back.** Commit per logical step with a
   descriptive message that starts with the WP id, e.g. `WP-18: add
   locomotion/turn clips from Animset Pro (6 files)`. Never use a generic
   "Update Felt assets" commit. **Don't run `UpdateFelt.ps1`**: it does a
   blanket `git add -A` + generic commit. Export Godot directly (see the
   context doc). Library moves/renames go in their own commit, separate from
   additions, so a bad reshuffle can be reverted alone. Mario: "this way we
   can roll back some animation sorting bs from gemini".
8. **Licences**: every downloaded asset gets a `CREDITS.md` line (source URL,
   author, licence). CC0 / CC-BY only, unless Mario approves otherwise. Booth
   items go on a shortlist for Mario; don't log in anywhere.

## Prompt to start a session (Mario pastes this into Antigravity)

> You are implementing one work package for the Felt project. Read, in
> order: `E:\Felt\docs\plans\impl\00-implementer-context.md`,
> `E:\Felt\docs\plans\impl\DELEGATION.md`, then
> `E:\Felt\docs\plans\impl\WP-32-33-wardrobe-automation.md`. Implement **WP-33
> only** (or WP-32 if told). Follow the DELEGATION.md rules exactly: evidence
> for every claim under `### Proof`, gaps under `### Not done / unverified`,
> status `🔎 needs review` in the README (never ticked by you). Stop when the
> WP's acceptance checks are met or you're blocked on Mario (the gallery
> review).

## Verification (Claude's side, after a delegated WP)

Claude checks the `### Proof` against reality: files exist, a sample renders
correctly, tests or commands re-run clean, nothing outside the WP changed
(`git status` / `git diff --stat` in each repo). Only then does the WP get
ticked. Anything that doesn't match gets written up in the WP notes as a
finding. Systematic misses go into this file as a new rule.
