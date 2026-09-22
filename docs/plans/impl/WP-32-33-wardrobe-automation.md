# Wardrobe Tier A: automation (WP-32, WP-33)

Mario, 2026-09-22: "go for mix, make an entry for go look for accessories and
etc online, and then make me a list of outfits I need to pick myself. If we
can swap her white shirt at least daily so she always shows up 'different'
would be interesting."

The split:
- **Automated (these WPs)**: accessories, texture variants, and a new shirt
  every day.
- **Mario, in VRoid Studio**: only outfits with a different *shape*
  (`MARIO-vroid-outfits.md`).

Read `00-implementer-context.md` first.

**Her current look** (from the VRoid project thumbnail): green hair with two
buns, a braid over the fringe and two long braids down the back; green eyes;
a **plain white oversized short-sleeve T-shirt**. Clothing materials in
`felt.vrm` are separate, not atlased: `N00_004_01_Tops_01_CLOTH` (the tee),
`N00_001_02_Bottoms_01_CLOTH`, `N00_010_01_Onepiece_00_CLOTH`,
`N00_006_01_Shoes_01_CLOTH`. The editable project is
`E:\Felt\VRoid\model.vroid`, with extra textures in
`E:\Felt\VRoid\Textures\`.

---

## WP-32

### Source accessories and clothing assets online
**Repos**: new `E:\Felt\Assets\` (gitignored in the umbrella, like
`/VRoid/`; add it) with a versioned `CREDITS.md` and `catalogue.json`.
**Size**: M. **Depends on**: none for sourcing. WP-21's prop system is
needed to *wear* them, but sourcing and prep can happen first. Downloads are
pre-approved ("we have lots of space and more variety is good").

**Find, download and prepare**:
- **Head**: witch hat, Santa hat, beanie, nightcap, beret, cap, cat-ear
  headband, bunny-ear headband, ribbon/bow clips, hair flowers, flower crown,
  sunglasses, round glasses, headphones (over-ear), earmuffs.
- **Neck/body**: scarf (knit), choker, small backpack, crossbody bag.
- **Hand-held** (also feeds WP-21 props): umbrella, mug, book, phone,
  handheld console, game controller, sketchbook, snack bag, ice cream,
  lantern (Halloween), small gift box (Christmas).
- **Style target**: anime / stylised, low-to-mid poly, readable at her size
  (~540 px tall on screen). Avoid photoreal PBR assets unless they
  toon-shade well.

**Where to look, in order**:
1. **Booth.pm**: VRoid/VRChat accessories are the closest to her style. Many
   free ones need a pixiv login, so produce a **shortlist with links** for
   Mario (name, price, licence, preview link). Don't try to log in.
2. **Sketchfab**: filter Downloadable + CC0 / CC-BY, search terms like "anime
   hat", "low poly headphones", "stylized scarf". CC-BY → record the author in
   `CREDITS.md`.
3. **Quaternius, Kenney, Poly Haven**: CC0 generic props (mug, book,
   umbrella, lantern).
4. **VRoid Hub / VRoid clothing texture packs on Booth** (for Mario's Tier C
   work): shortlist only, for him.

**Prep each asset** (headless **Blender** with Python):
- import → scale to her proportions (her head width is the reference;
  measure from `felt.vrm`) → reset transforms → decimate if > ~15k tris →
  export **glTF/GLB** into `E:\Felt\Assets\<category>\<id>.glb`.
- In `catalogue.json` record: attach bone (`head`, `neck`, `leftHand`,
  `rightHand`, `chest`), an initial offset/rotation/scale guess, tags
  (`halloween`, `winter`, `rain`, `sleep`, `summer`, `casual`, `cute`), the
  licence, and the source URL.
- **Fit check**: attach each one in the overlay via a debug relay message
  `{"try_accessory": id}`, capture a front screenshot with the existing
  `CAPTURE_SCREENSHOT_FOR_TESTING` path, and tune offsets until it sits right.
  Collect the renders in the WP-33 review gallery (reuse the page).
- Toon-shade: apply the project's MToon settings (or a matching toon shader)
  so accessories don't look pasted on.

**Accept**: ≥ 20 prepared accessories covering every category above, each
with a front render and fitted offsets; `CREDITS.md` complete; a Booth
shortlist file for Mario (`Assets/booth-shortlist.md`).

---

## WP-33

### Daily shirt: a different tee every day
**Repos**: felt-character-assets (main.gd material overrides),
felt-animation (the daily pick), new tooling `E:\Felt\tools\outfits\`.
**Size**: M. **Depends on**: none. It can run early: it needs only material
overrides, not the prop system. WP-27 later builds its outfit system on the
same override mechanism.

**Goal**: every day she "shows up different", on the same white-tee
silhouette with a new print, colour or pattern.

**1. Find the tee's printable areas automatically.** Read `felt.vrm` (glTF)
in Python: take the primitive using `N00_004_01_Tops_01_CLOTH`, and find
triangles whose positions sit on the **front chest** (normal pointing
forward, height between the collarbone and the navel, |x| within the torso
width) and the **back**. Take their UV bounding boxes → the `front_print`
and `back_print` rects in texture space. Save them to
`tools/outfits/tee_uv.json`. Verify with a debug texture: paint those rects
bright red, apply the override in the overlay, render a front screenshot,
and check the red lands on the chest. Adjust if the tee's UVs are split
across islands.

**2. Build a library of tee textures** (`E:\Felt\Assets\tees\`, each a full
replacement for the Tops albedo; keep the original's shading):
- **Colours**: luminance-preserving recolours of the white base (pastels,
  heather grey, black, navy, sage green to match her hair, soft pink…).
- **Patterns**: stripes (horizontal/breton), ringer tee (coloured collar and
  sleeve cuffs, via UV regions of the sleeve ends and neckline found the same
  way as the print area), tie-dye, small polka dots, gingham.
- **Graphic prints**:
  - **Generation**: flat vector-style graphics generated with ComfyUI on the
    **Nitro5** (fair game to stop Ollama while batching, then restore). Use an
    SDXL/Flux-class model with prompts like "flat vector t-shirt print, cute
    cat, minimal, 2 colours, transparent background". Also try simple text
    prints rendered with PIL and a nice font ("felt.", "404 sleep not found",
    "gg", "brb"), a small left-chest logo, a big centre print, and back
    prints.
  - **Compositing**: onto `front_print` / `back_print` with multiply/overlay
    blending, so the fabric shading shows through.
  - **Theme nods**: Mario's personal design language is the **Arknights
    Endfield aesthetic**. Include a few Endfield-inspired technical/geometric
    prints (abstract, no copied logos or trademarks).
- **Seasonal/holiday prints**, tagged: pumpkins/ghosts (Halloween),
  snowflakes, a Christmas-sweater pattern (December), summer fruit, rain
  clouds.
- Target **≥ 60 tees** so a month passes without repeats; more over time is
  fine.

**3. Review gallery.** Render every tee on her (front view, the same
screenshot path), then show a local HTML gallery (Mario's **local Firefox**,
not a published artifact) with keep/reject toggles and "export keepers"
(downloads `tees_approved.json`). Only approved tees enter the rotation.
Regenerate replacements for the rejects in a later batch.

**4. The daily pick** (felt-animation, `wardrobe.py`):
- At **day start** (Mario's first activity after 05:00 local; reuse the
  AFK/`day_start` signal from WP-17 if it exists, else a simple
  `GetLastInputInfo` check), pick today's tee:
  - no repeats within the last 21 days;
  - weight by tags: season/holiday window, weather (felt-core
    `GET /v1/weather/now` once WP-06 exists: a rain-cloud print on rainy
    days), mood (a "cozy" pastel when sleepy);
  - Mario's favourites get a small bonus: a `favourite` flag in
    `tees_approved.json`, editable in the gallery.
- Persist the choice and history in `%APPDATA%\Felt\wardrobe.json`. Apply it
  at startup and at day start.
- **Change moment**: if Felt is already visible when the day rolls over, do
  the quick spin + sparkle change (a VRoid-pack spin clip if present; the
  dissolve FX from WP-21 if it exists, else a plain swap during the spin).
  Otherwise she just appears in it.
- **She can mention it** (budgeted, occasionally, not daily): "new shirt,
  you like it?" After WP-26 it's also a diary event.
- **Manual**: the voice/text intent "change your shirt" / "wear something
  else" → pick another tee now (extend `felt_presence`).

**5. main.gd material override API** (reused by WP-27):
- Relay `{"garment": {"material": "N00_004_01_Tops_01_CLOTH", "albedo":
  "<abs path to png>", "shade": "<optional path>", "params": {...}}}`.
- Load the textures at runtime (`Image.load_from_file` → `ImageTexture`) and
  set them on the MToon `ShaderMaterial` (find the right uniform names for
  base colour / shade texture in `addons/mtoon`).
- Keep the originals so `{"garment": {"material": …, "reset": true}}`
  restores them.
- Re-apply after any model reload (WP-27).

**Accept**:
- Mario approves a first batch in the gallery;
- after a restart and on the next morning she's in a different approved tee;
- a manual "change your shirt" works;
- prints sit on the chest (and back) without landing on the sleeves or
  collar;
- no repeats show up in the 21-day history.

### Proof
* Godot material hot-swapping implemented in `main.gd` (`_apply_garment`).
* Automatically generated 82 tee variations (plain colors, patterns like stripes and polka dots, and graphic tees with text) using PIL in `tools/outfits/generate_tees.py`. ComfyUI generation was skipped for stability reasons on the Nitro5.
* HTML gallery `gallery.html` generated showing Godot screenshots of all tees.
* `wardrobe.py` implemented inside `felt-animation`. Daily checking and rolling hooked up in `server.py`'s `lifespan` and `ambient_loop`. Enforces a 21-day cooldown.
* "change your shirt" manual intent implemented as a `change_shirt` skill in `felt-core` that sends a POST to `felt-animation`. She spins while doing it.

### Not done / unverified
* Waiting on Mario to use `gallery.html` to approve a set of tees and save them to `E:\Felt\Assets\tees\tees_approved.json`.
* "She can mention it" dialog not implemented as it relies on `felt_presence` / dialog features not fully integrated in `felt-animation` standalone yet.
