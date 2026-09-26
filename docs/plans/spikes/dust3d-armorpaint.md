# Spike: Dust3D and ArmorPaint for future model generation

Mario, 2026-09-26: flagged both tools as "interesting for possible models
down the line, if we ever pick up the model generation again." This is a
**read-only research spike** — nothing installed, nothing run, no service
touched. Scope: could either tool help with WP-21 props (chest, chair, mug,
headphones, umbrella…) or WP-27/32 wardrobe (VRoid outfits/accessories),
and how would either sit next to the existing pipeline (Blender `bpy`
scripting, ComfyUI on the Nitro5, the paused TripoSR image-to-3D effort
documented in `runbooks/felt-overlay-3d-pipeline.md`).

**Verified vs inferred**: facts pulled straight from the GitHub API
(`api.github.com/repos/...`) or fetched project pages are marked
**Verified**. Judgment calls about fit, quality, and things not directly
tested (e.g. whether Smart App Control actually blocks these specific
binaries on Mario's box) are marked **Inferred** — flagged so a future
pass knows what still needs a hands-on check.

## Dust3D

**What it is**: free, open-source (MIT) cross-platform low-poly 3D
modeling tool (huxingyi/dust3d). Core workflow: sketch a skeleton of
nodes/edges on a 2D canvas, a 3D mesh generates in real time; label edges
with bone names for auto-rigging (auto skeleton + skin weights); comes
with procedural animation cycles (walk/run/attack/idle/death); single app
covers sketch → UV unwrap → texture → rig → animate → export. **Verified**
(dust3d.org, GitHub repo).

- **Maturity/activity, Sept 2026**: **Verified** via GitHub API —
  3,553 stars, not archived, `pushed_at: 2026-08-17`, latest release
  **1.1.6** published 2026-06-08. Genuinely alive, but small-scale: 10 open
  issues, effectively a solo-maintainer (huxingyi) project, 1 open PR. Not
  enterprise-grade, but not abandoned either.
- **License**: MIT. **Verified**.
- **Export formats**: GLB and FBX. No plain OBJ mentioned. **Verified**
  (project docs).
- **Windows build**: a plain unsigned zip (`dust3d-1.1.6.zip`, ~18MB,
  4,974 downloads on that release — **Verified** via GitHub API asset
  list). The project's own site tells users to expect a Windows
  SmartScreen warning and click "More info → Run anyway" (**Verified**,
  dust3d.org). No code signing evidence anywhere. **Inferred**: Smart App
  Control is stricter than SmartScreen (no user click-through, it just
  blocks) — this build should be assumed **blocked outright** on Mario's
  desktop until proven otherwise. Two ways around it if this gets picked
  up: run it through the `ClaudeElevated`/SAC-exception path if one gets
  added to the allowlist, or build it from source (MIT license permits
  this, Dust3D is a Qt6 CMake project — plausible but untested effort).
- **Scriptable/CLI**: none found. No headless mode, no command-line batch
  export, no plugin/scripting API in any docs or release notes. It's a
  GUI-only sketch tool. **Inferred** (absence of evidence across the repo,
  docs site, and release notes, not an exhaustive source-code read).
- **Output quality for stylised props**: genuinely fits — it's explicitly
  aimed at low-poly game-ready meshes, not photoreal, so a flat/toon MToon
  shader should sit naturally on its output. **Inferred** from stated
  purpose, not from an actual render test.
- **VRoid outfit fit**: **probably not**, as guessed in the brief. Dust3D's
  auto-rig builds a skeleton *from scratch* out of its own sketched edges;
  it has no concept of fitting a garment mesh onto an *existing* external
  humanoid rig (VRM/VRoid's `J_Bip_*` bone convention, a specific bind
  pose). It's a whole-model creator, not a garment-fitting tool. **Inferred**
  from its documented feature set — no direct test of a garment workflow
  was attempted (there is no such documented workflow to test).

## ArmorPaint

**What it is**: standalone PBR texture painter — node-based procedural
materials/brushes, real-time path-traced viewport, layer painting, live-link
plugins for Blender/Unity/Unreal. Part of the wider Armory3D ecosystem
(Armory engine, ArmorLab/ArmorForge). **Verified** (armorpaint.org).

- **Big news right in this window**: **ArmorPaint 1.0 shipped ~2026-09-12**,
  after 8 years in early access — a full rewrite from Haxe/Kha (V8 JS
  engine) to plain C, smaller and faster, GPU backends now Direct3D 12 /
  Vulkan / Metal / WebGPU depending on platform. **Verified** (CG Channel,
  Digital Production coverage; GitHub API shows `armory3d/armorpaint`
  `pushed_at: 2026-09-24`, 5,194 stars, 96 open issues — actively worked on
  right now).
- **AMD GPU support**: Vulkan and Direct3D 12 backends mean the RX 6700 is
  supported natively — no CUDA/NVIDIA-only lock-in unlike a lot of AI
  texture tooling. **Verified** (release coverage), not hands-on tested.
- **License model**: source is open under a zlib/libpng-style license
  (`github.com/armory3d/armorpaint`, buildable for free); official compiled
  binaries are commercial — **$19 on itch.io** (also $17.99 iOS / $19.99
  Android). Pay-for-binary, free-to-self-build, funds ongoing dev.
  **Verified**.
- **Windows/SAC**: no evidence found either way of Authenticode signing on
  the itch.io binary. **Inferred**: as a small indie itch.io distribution,
  most likely unsigned like Dust3D, and would probably hit the same Smart
  App Control block — needs an actual hands-on check (or building from
  source, which the zlib license allows) before relying on it.
- **AI texture features ("Neural Nodes")**: 1.0 folds ArmorLab-class
  generative features directly in — text-to-image, image-to-PBR-texture
  extraction, 4x upscaling — and runs them **locally**, not cloud-based.
  **Verified** (CG Channel). Whether standalone ArmorLab/ArmorForge apps
  still exist separately from this or are being folded in/deprecated is
  unclear post-1.0 and worth re-checking before adoption — flagged, not
  resolved, here.
- **Scriptable/plugin API**: 1.0 replaced the old Haxe/JS plugin system
  with a custom minimal interpreted-C dialect (example: `hello_world.c` in
  `data/plugins/`). Public docs online largely describe the pre-1.0 Haxe
  system and are stale for 1.0. **Verified** (GitHub issues, repo).
  Notably, a **third-party** project — `darenceey/armorpaint-mcp` on
  GitHub — already bridges an MCP client (e.g. Claude) to ArmorPaint 1.0
  through this C plugin dialect plus a file-based IPC mailbox, exposing
  ~58-88 tools (project management, material/node editing, painting/fill,
  export). Its own README: Linux fully verified, Windows "core tools
  tested, window-capture/wake mechanisms unverified," macOS untested.
  **Verified** that the project exists and claims this; **not verified**
  that it actually works reliably on Windows. This is a real, if young and
  unofficial, path toward a scriptable ArmorPaint pipeline stage — genuinely
  promising, worth another look if it matures, not something to lean on now.
- **Fit for toon/anime textures**: **poor fit as designed**. The whole
  product — path-traced viewport, metalness/roughness workflow, real light
  simulation — is built for PBR realism, the opposite of MToon's flat-shaded,
  gradient-map, rim-lit look. It *could* still be used narrowly as a
  pattern/mask-painting tool (paint detail into just the albedo/base-color
  channel, discard the rest, feed only that into MToon), but that needs
  deliberate discipline to not lean on the features the product is actually
  built around. **Inferred** from documented feature set, no hands-on
  texture-painting test was run.

## Fit for Felt, tool by tool

**Dust3D → props (WP-21)**: the one plausible pipeline slot is
`Dust3D (sketch, auto-UV) → Blender (cleanup/scale/orientation sanity check)
→ glTF/GLB → Godot with MToon`, for a prop that isn't already covered by a
CC0 pack. It genuinely beats hand-modeling in Blender *for a from-scratch
low-poly shape*, on speed alone. It loses outright against just grabbing the
matching item from **Kenney Furniture Kit, Poly Haven, or Quaternius** (all
CC0, already UV'd, already toon-friendly) — WP-21's own catalogue already
names those as the first-choice source for exactly this list (chest, chair,
mug, headphones, etc. — see `WP-18-23-assets-world.md`). Dust3D only earns
its place for the rare item nothing CC0 covers, and even then it's a fully
manual, one-shot tool (no CLI/scripting) — not something that plugs into an
automated pipeline the way ComfyUI or Blender `bpy` scripts do today. Not
useful for VRoid outfits (wrong tool class, see above).

**ArmorPaint → props/wardrobe textures**: could sit at
`base mesh (Dust3D/Blender/CC0) → ArmorPaint (paint base-color detail) →
export texture → Godot/MToon` for a prop where hand-painted albedo detail
would actually read (a patterned mug, upholstery on the fancy chair). It
loses to **Blender's own texture-paint mode** — already in the toolchain
today, zero extra cost/install/SAC friction, plenty good for flat toon
color work — unless the specific procedural-pattern/node tools are wanted.
It loses entirely to CC0 packs (already textured). For **WP-32/33 wardrobe
textures specifically**: the actual current tooling (PIL-generated tee
patterns in `tools/outfits/generate_tees.py`, Booth-sourced texture packs)
already works and is far simpler than standing up a PBR-realism painter to
produce flat toon patterns — ArmorPaint would be the wrong tool here, not
a missing piece.

**Vs. AI 3D generation (TripoSR / Hunyuan3D / TRELLIS, briefly)**: those
take a 2D image and reconstruct an organic mesh automatically — already
tried for the character itself (see `felt-overlay-3d-pipeline.md`), and
ultimately dropped in favor of a real VRoid-made model because the
auto-rigged/reconstructed result needed too much manual rig/cloth-physics
repair to look right. Dust3D and ArmorPaint are a different category
entirely — human-driven, parametric/manual tools for simple hard-surface
low-poly objects and their textures — lower risk, lower "magic," but also
a smaller ambition (no one-shot character generation). For simple props
they're plausibly a *better* fit than the AI-reconstruction route ever was,
precisely because props don't need a humanoid rig or cloth physics.

**Effort and risk**: both tools are small, free downloads to trial
(Dust3D outright free; ArmorPaint's source is free to self-build, or $19
for a binary) — low financial risk. The real friction is Smart App Control:
both Windows builds are, as best determined without hands-on testing,
unsigned, so expect a block on first run and a real decision (SAC
exception, or self-build from source) before either is usable at all.

## Verdict

- **Dust3D — keep in mind, for props only.** Free, MIT, genuinely active
  (pushed 2026-08-17), purpose-built for exactly WP-21's low-poly prop
  need — but only worth reaching for the rare item no CC0 pack already
  covers, since it has no automation/CLI (manual one-off tool, not a
  pipeline stage) and will likely need a Smart App Control workaround
  before it even runs. **Not** for VRoid outfits — wrong tool class
  (whole-mesh sketch tool, not a garment-fitting tool).
- **ArmorPaint — skip for now, keep in mind narrowly.** Genuinely
  strong and freshly rewritten (1.0 shipped 2026-09-12, AMD-friendly via
  Vulkan/D3D12), but fundamentally a PBR-realism tool that fights MToon's
  flat toon look, costs $19 for the official binary, and is (best-inferred)
  unsigned like Dust3D. Current WP-21/32/33 tooling (CC0 packs, Blender
  texture paint, PIL-generated tee patterns) already covers the actual
  need more simply. The one reason to revisit: the unofficial
  `armorpaint-mcp` bridge, if it matures and gets proven on Windows, would
  make automated painterly-pattern generation for props genuinely
  scriptable — worth a 30-minute look if that project matures, not now.
- **First concrete mini-experiment, if model generation gets revived**:
  pick one WP-21 prop *not* available in Kenney/Quaternius/Poly
  Haven/Sketchfab CC0 (e.g. the "fancy chair" or "chest"), build it in
  Dust3D (sketch → auto-UV → GLB export, timeboxed 30-60 min), pull it
  into Blender for a scale/orientation check, and see whether the flat
  MToon shader looks right on its output untouched. That answers "is
  Dust3D's stylised low-poly output actually good enough" directly,
  without touching ArmorPaint or reopening the paused
  TripoSR/character-model-gen effort at all.

## Sources

- https://dust3d.org/
- https://github.com/huxingyi/dust3d
- https://github.com/huxingyi/dust3d/releases
- https://api.github.com/repos/huxingyi/dust3d (stars/pushed_at/release-asset data, queried 2026-09-26)
- https://community.chocolatey.org/packages/dust3d
- https://armorpaint.org/
- https://armorpaint.org/manual
- https://github.com/armory3d/armorpaint
- https://api.github.com/repos/armory3d/armorpaint (stars/pushed_at, queried 2026-09-26)
- https://www.cgchannel.com/2026/09/armorpaint-1-0-is-out-after-eight-years-in-early-access/
- https://digitalproduction.com/2026/09/12/armorpaint-1-0-swaps-haxe-for-c/
- https://github.com/darenceey/armorpaint-mcp
- https://github.com/armory3d/armorlab_docs (ArmorLab context)

## Related project docs read for context

- `F:\workspace\runbooks\felt-overlay-3d-pipeline.md` — the paused
  TripoSR image-to-3D character pipeline (why it was set aside).
- `F:\workspace\runbooks\felt-overlay-3d-render-spike.md` — overlay
  rendering history, largely superseded by the Windows/Godot pivot.
- `E:\Felt\docs\plans\impl\WP-18-23-assets-world.md` — WP-21 props system
  and its CC0/Sketchfab source catalogue.
- `E:\Felt\docs\plans\impl\WP-32-33-wardrobe-automation.md` — wardrobe
  automation, current PIL-based texture generation and Booth sourcing.
