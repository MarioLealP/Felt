# Phase 6 — "Life" features (WP-25 … WP-31)

Chosen by Mario on 2026-09-22 from a follow-up brainstorm. He kept the PoE2
companion, the diary, the wardrobe, screen-matched lighting, AFK hobbies and
calendar heads-ups; **especially the diary and the wardrobe**. He dropped the
OBS "clip that" auto-highlights and the Home Assistant/ntfy alerts. Read
`00-implementer-context.md` first. One WP per session.

---

## WP-25

### Proactive channel: felt-core → desktop pushes
**Repos**: felt-core (deploy), felt-tray. **Size**: S–M. **Depends on**:
WP-09.

**Why**: several features below need the *server* to start a remark (the
calendar heads-up, the diary morning greeting). Today everything is
desktop-initiated (request → reply), and there's no server → desktop path.

**Do**:
- felt-core: a `proactive` queue (SQLite table `proactive(id, kind, text,
  payload_json, created_at, expires_at, delivered_at)`) and a **long-poll**
  endpoint `GET /v1/proactive/next?timeout=25`. It returns the next
  undelivered, unexpired item, or 204 on timeout. It marks the item delivered.
  An item carries `text` (already phrased), an optional `animation_tag`, and
  `emotion`. The TTS WAV is fetched separately via `GET /v1/proactive/{id}/audio`
  (reuse the WP-06 TTS cache).
- felt-tray: a background thread long-polls it. For each item, POST it to
  felt-animation `/reply_ready` with `prompted=0` (so hush, ducking, bubble
  and cooldown rules all apply desktop-side). Skip it (don't lose it: requeue
  via `POST /v1/proactive/{id}/requeue`) while Felt is hidden or away, unless
  `kind` is `urgent` (the calendar heads-up ≤ 10 min).
- Expiry matters: a heads-up for an event that has already started is
  useless, so drop it.

**Accept**: an item inserted via a debug endpoint (`POST
/v1/proactive/debug`, only when `FELT_DEBUG=1`) is spoken on the desktop
within ~2 s; an expired one never is.

---

## WP-26

### The diary: day-to-day continuity  ★ Mario's priority
**Repos**: felt-core (deploy), felt-animation (event reporting),
felt-dashboard (a read view, if Mario wants it; see the open question).
**Size**: M. **Depends on**: WP-07, WP-15, WP-25. WP-17 enriches it.

**Why**: being remembered across days is one of the strongest "she's real"
signals. Today she has the last 20 messages and nothing else.

**Material** (all already collected, or collected by earlier WPs):
- screen observations (the `seen` text from WP-07, already cloud-safe);
- her spoken reactions;
- desktop **events** reported by felt-animation to a new felt-core endpoint
  `POST /v1/events` (`{kind, data, at}`): `game_start/stop` with names and
  durations, `afk_start/end`, `music_track`, `mash`, `gpu_hot`, hush
  used, window falls, props she used, hobby sessions (WP-30);
- the WP-16 music taste table;
- the mood trajectory (felt-animation sends a mood snapshot hourly as an
  event).

**Privacy**: the diary text itself is fed into *cloud* prompts later, so it
must be built **only from cloud-safe material**. Screen `seen` text, events,
music and mood are safe. **Chat messages** go in only as a whole window that
passes `is_safe_for_cloud`; otherwise they're left out entirely (not
summarised locally into the diary). Facts are never used.

**Writing**:
- Once per day, triggered by Mario's first activity after 05:00 local (the
  desktop sends an `afk_end`/`day_start` event), felt-core writes
  **yesterday's entry**.
- It uses `cloud_generate("summary", …)` on the volume model (Gemma), JSON
  mode → `{"entry": "<first-person diary in her voice, 120–250 words, playful,
  about *their* day together>", "callbacks": ["<short hooks worth bringing
  up later, e.g. 'rage-quit Elden Ring after 3 deaths to the same boss'>",
  …up to 5], "mood_word": "…"}`.
- Store it in a `diary(date PRIMARY KEY, entry, callbacks_json, mood_word,
  created_at)` table.
- **Compression**: on Sundays, the previous week's entries are condensed into
  a `diary_weeks(week, summary, callbacks_json)` row. Monthly the same for
  weeks. The daily rows stay (they're small).

**Using it**:
- **The system prompt for chat and screen reactions** gets a compact
  "Recently (from your diary): yesterday: <mood_word>, <2 callbacks>; this
  week: <1–2 lines>". Keep it under ~120 tokens.
- **Morning greeting**: after writing the entry, enqueue (WP-25) one
  proactive line referencing yesterday. It's budgeted: one per day, and never
  if Mario was AFK all day.
- **Callbacks decay**: each callback is used at most twice, then retired.
  Track it in `callbacks_json`.
- She can answer "what did I do yesterday?" / "how was my week?" (a
  `diary_recall` intent in the `felt_presence` skill, or a small new skill,
  class `public`).

**Decided (Mario, 2026-09-22): readable and cheeky.**
- **A "Felt's diary" page in felt-dashboard**, newest first, each entry with
  its date and mood word. Written *knowing Mario reads it*: playful, teasing,
  affectionate ("he died to the same boss four times and then blamed the
  controller"). Put that in the writing prompt explicitly.
- **Mario can correct her memory**: each entry has delete and edit actions
  (`PATCH/DELETE /v1/diary/{date}`). An edited entry is marked as edited,
  and its callbacks are regenerated from the new text.
- The page reads `GET /v1/diary?limit=30` plus the weekly summaries. The
  dashboard is LAN-only, like the rest of felt-core's API.

**Tests**: material selection excludes unsafe chat windows and facts;
callback decay; the weekly compression trigger; prompt snippet length.

**Accept**: after a real day of use, the next morning she greets Mario with a
line that clearly references yesterday. `GET /v1/diary?date=` shows a sensible
entry. The prompt snippet shows up in chat/screen calls (check the logs at
DEBUG).

---

## WP-27

### Wardrobe: outfits by time, weather, season and mood  ★ Mario's priority
**Repos**: felt-character-assets (main.gd, models), felt-animation
(decisions), felt-core (weather hook, deploy). **Size**: L. **Depends on**:
WP-21 (the dissolve FX), WP-15 (mood). WP-06 for weather.

**Source material (checked 2026-09-22)**:
- Felt's **editable VRoid Studio project is `F:\workspace\model.vroid`**
  (loose in the workspace root).
- `F:\workspace\Vroid\` holds `Accessories/` (a free pearl earring set),
  `Textures/` (shoes, socks, hair), `Output/Felt.vrm`, and
  `Animations/VRMA_MotionPack` (the official VRoid VRMA pack).
- The runtime model is `E:\Felt\Model\felt.vrm` (junction to
  `felt-character-assets/felt-godot-overlay/characters/felt.vrm`).

**Step 0: done 2026-09-22.** `model.vroid` and the `Vroid\` folder now live
in **`E:\Felt\VRoid\`**:
- `model.vroid`, `Accessories/`, `Animations/VRMA_MotionPack/`,
  `Output/Felt.vrm`, `Textures/`.
- The copy was hash- and size-verified before the originals were removed.
- `F:\workspace\Vroid` is now a junction to it.
- It's gitignored in the umbrella repo (`/VRoid/`).
- It deliberately isn't under `E:\Felt\Model`: that's a junction *into the
  Godot project* (`felt-godot-overlay/characters`), and Godot would import
  every texture in there.

### Tiered approach (decided after checking the model, 2026-09-22)

Mario asked whether outfits can be automated or whether he should "churn
outfits on the side". The facts:
- **`.vroid` can't be scripted.** It's a ZIP containing `meta.json` and one
  opaque binary `v1model/data.bin`, with no public format. Garment *shapes*
  can only be made in VRoid Studio (GUI).
- **The exported VRM keeps clothing on separate materials**:
  `N00_004_01_Tops_01_CLOTH`, `N00_001_02_Bottoms_01_CLOTH`,
  `N00_010_01_Onepiece_00_CLOTH`, `N00_006_01_Shoes_01_CLOTH`, each with its
  own texture (not an atlas). So each garment's *look* can be changed at
  runtime by swapping or tinting that material's textures, with no new VRM,
  no model reload, and no retargeting.

**Mario confirmed the mix of both tiers (2026-09-22).** Tier A is split into
its own WPs so it can start early:
- [WP-32](WP-32-33-wardrobe-automation.md#wp-32): sourcing accessories and
  clothing assets online;
- [WP-33](WP-32-33-wardrobe-automation.md#wp-33): **a new tee print/colour
  every day**. He wants her to "always show up different". It also builds
  the garment-override API this WP reuses.

Tier C is his checklist, [`MARIO-vroid-outfits.md`](MARIO-vroid-outfits.md).
This WP then ties them together: outfit definitions, triggers, and the
model-swap path.

**Tier A: automated (implementer does this first; Mario only reviews)**
- **Outfit = base VRM + per-garment texture overrides + accessory props.**
  In main.gd, `{"outfit": id}` applies material overrides on the clothing
  surfaces (albedo + shade textures, MToon colour params) and attaches or
  detaches accessory props (the WP-21 system: witch hat, Santa hat, scarf,
  beanie, nightcap/sleep mask, glasses, headphones, umbrella, plus the
  blanket prop for pajama time). The swap is instant, so the spin/dissolve
  choreography below still covers it.
- **Generating texture variants** (offline tooling under
  `E:\Felt\tools\outfits\`):
  - **Palette recolours** with a Python/PIL script: luminance-preserving hue
    and saturation remaps per garment, so the shading baked into VRoid
    textures survives. Seasonal palettes: autumn/Halloween orange-black,
    Christmas red-white-green, winter cool, summer light, "cozy" pastel for
    night.
  - **AI restyles** via **ComfyUI on the Nitro5** (fair game now): img2img
    of each garment texture at low denoise, with tile/lineart ControlNet so
    the UV layout and seams stay aligned. Gives patterns and prints (plaid,
    stars, snowflakes, pumpkins). Expect some unusable results; that's what
    review is for.
- **Automatic preview renders**: for each variant, run the overlay's
  existing `CAPTURE_SCREENSHOT_FOR_TESTING` path (or a small headless variant
  of it) with the outfit applied, so there's a front-view PNG per variant.
- **Review gallery**: a local HTML page (open it in Mario's local Firefox,
  not an artifact) showing the renders with keep/reject buttons. The keepers
  go into `outfits.json`.
- Starter set from Tier A alone: default, cozy-night (pastel recolour +
  nightcap + blanket), Halloween (recolour + witch hat), Christmas
  (recolour + Santa hat + scarf), rainy (recolour + umbrella), winter
  (recolour + beanie + scarf), summer (light recolour + sunglasses).

**Tier C: Mario, on the side, whenever he feels like it**: **new garment
shapes** that recolours can't fake. Proposed first: real pajamas, a
hoodie, a raincoat or winter coat. In VRoid Studio:
- open `E:\Felt\VRoid\model.vroid` → *Save As* a variant;
- change **only** clothing and accessories. **Never** body, face or hair,
  so the skeleton, blend shapes and proportions stay identical;
- export with the **same settings** as the current `felt.vrm` (VRM 1.0,
  separate materials, no atlas or reduction changes), named
  `felt_<outfit>.vrm`.

Each Tier-C VRM also gets Tier-A treatment (recolours and accessories on top
of it). The runtime needs the model-swap path described below only for these.

Clothing sources for Tier C: VRoid's built-in items, Booth.pm VRoid clothing
textures (many free; pixiv login needed, so Mario), and the textures in
`E:\Felt\VRoid\Textures`.

### Runtime model swap (only needed once Tier-C outfits exist)
- The `{"outfit": "<id>"}` relay message covers both tiers. The outfit's
  entry says whether it needs a different VRM.
- **First check whether a model swap can reuse the retargeted
  `AnimationLibrary`.** If every outfit VRM has identical bone names and rest
  poses (it should, from the same base), the library can move to the new
  instance without re-running `_load_vrma_corrected_retarget` for every clip.
  If not, preload and retarget in a background thread when an outfit change is
  scheduled, so the swap itself is instant.
- **Swap choreography** (felt-animation decides, Godot executes):
  - **Quick change**: a VRoid-pack `Spin` or a twirl clip. At the peak of the
    spin, a sparkle burst plus a fast dissolve-swap of the model (reuse the
    WP-21 dissolve shader, applied to all materials).
  - **Proper change**: she walks off-screen ("brb, changing"), and comes back
    in the new outfit. Used for bigger changes like pajamas at night.
- Re-apply everything that's per-model: MToon tuning (`_tune_mtoon_materials`),
  blink/expression/mouth shape caches, spring-bone reinit, the feet clamp,
  bubble anchor bones.

**Deciding what she wears (felt-animation, `outfits.json`, data)**:
```json
{"outfits": [
  {"id": "default", "vrm": "felt.vrm", "tags": ["default"]},
  {"id": "pajamas", "vrm": "felt_pajamas.vrm", "tags": ["sleep"], "when": {"hours": [0, 6], "or_mood": "sleepy"}},
  {"id": "raincoat", "vrm": "felt_raincoat.vrm", "tags": ["rain"], "when": {"weather": ["rain", "storm"]}},
  {"id": "halloween", "vrm": "felt_halloween.vrm", "tags": ["season"], "when": {"dates": ["10-24", "11-01"]}}
]}
```
- Priority: holiday > weather > time/mood > default.
- **Hysteresis**: at most one change per ~2 h, unless the trigger is strong
  (sleep time, a holiday starting).
- Occasionally a random "feeling cute" change between allowed outfits
  (low weight).
- A **manual** change via keybind or voice ("change into your pajamas",
  "wear something else"): extend `felt_presence`.
- Weather comes from felt-core's WP-06 weather cache via a small
  `GET /v1/weather/now` (condition code only).
- The outfit change is a diary event (WP-26) and can get a line ("rain
  again, raincoat time").

**Build order**: Tier A (texture overrides + accessories + tooling + gallery)
first, without waiting for Mario. The model-swap path only once his first
Tier-C VRM arrives.

**Accept**: Tier-A outfits approved by Mario in the gallery are live; she changes with the spin/dissolve
without a visible hitch; the triggers work (force the time/weather via debug
endpoints); face, lips, blink, hair physics and floor clamp all still work
after a swap.

---

## WP-28

### Screen-matched lighting + contact shadow
**Repo**: felt-character-assets (main.gd), felt-tray or felt-animation
(colour sampling). **Size**: M. **Depends on**: WP-07 (window
identification + blocklist).

**Why**: she looks pasted on top of the desktop. Matching the light to
what's behind her makes her look like she's *in* the scene.

**Do**:
- **Sampling** (local only, nothing stored or sent): every ~1 s, take the
  on-screen region behind and around her (her bounding box, expanded ~50 %),
  grab it at tiny resolution (e.g. 16×16), and compute (a) the average colour,
  (b) the dominant bright colour, (c) luminance.
  - **Respect Mario's capture blocklist**: if a blocklisted window
    (Discord, browsers, File Explorer, WhatsApp, Telegram, Phone Link,
    KeePassXC, banking) intersects that region, **don't sample**; fade to
    neutral lighting instead. The blocklist check comes from WP-07's policy
    module. Never persist or transmit pixels; note this in the code.
  - Exclude FeltOverlay's own window from the grab. Use
    `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` on the overlay if
    needed, which also keeps her out of WP-07 captures.
- **Apply** (main.gd, new relay message `{"ambient_light": {"rgb": [...],
  "key_rgb": [...], "lum": 0..1}}`):
  - ease the rim/fill light colours toward the dominant colour (clamped
    saturation, so she never turns neon);
  - scale the ambient/indirect intensity with luminance (a dark game → a
    slightly darker her);
  - transition over ~1.5 s;
  - keep her readable, with floors on the key light intensity.
- **Contact shadow**: a soft blob-shadow decal/quad under her feet (a radial
  gradient texture, alpha ~0.35, scaled with the feet spread), following her.
  It darkens the desktop pixels under her feet via normal alpha blending in
  the transparent window.

**Accept**: over a bright white window vs a dark game she visibly picks up
the scene's tint without looking odd; the blob shadow grounds her; with a
browser behind her, the lighting goes neutral (and the logs show it skipped).

---

## WP-29

### Path of Exile 2 companion
**Repos**: felt-core (deploy), felt-tray (WP-07 app hook). **Size**: M.
**Depends on**: WP-07, WP-06.

**Existing pieces**: `plugins/poe_price_check/` (a price-check skill with a
trade cache, `poe_trade_cache.py`) and the **poe2-rag** service on the
server (Path of Exile 2 wiki RAG; see `runbooks/poe2-rag.md`).

**Do**:
- In `/v1/react/screen` (WP-07), when `app` matches the PoE2 executable
  (confirm the real exe name on this machine, e.g. `PathOfExile*.exe`), use
  a **PoE-specific prompt**: identify notable things (a **unique item or
  currency tooltip**, a boss, death, a level-up) and return JSON with
  `items: [{"name", "kind": "unique|currency|other"}]` alongside the usual
  `line`/`emotion`.
- For each unique or currency item found, run the existing price check
  (through the skill's function directly, not the router), then produce the
  final line with the price ("ooh, a Headhunter, that's like 40 div"). Keep
  it to one extra model call at most. The price data is public, so the cloud
  is fine.
- **Build and mechanics questions** in chat ("what does X do?", "is Y good
  for my build?") → a skill that queries poe2-rag (check its API in the
  runbook), class `public`. Router examples are needed to separate it from
  `web_search`.
- The tone table applies: she's a hype loot goblin on big drops and teases
  bricked crafts.

**Accept**: hovering a unique/currency tooltip in PoE2 leads to a reaction
that includes a real price within the normal cooldown. A wiki question gets a
RAG-grounded answer.

---

## WP-30

### Hobbies while Mario is AFK
**Repos**: felt-animation, main.gd (via props). **Size**: M. **Depends on**:
WP-21 (props), WP-17 (AFK signal), WP-26 (diary events).

**Do**:
- On `afk_start` (> 10 min without input), she picks a **hobby** weighted by
  mood and time:
  - reading (book prop, a sitting/reading idle);
  - playing a handheld (game-controller or handheld prop, a sitting idle with
    small hand motion);
  - doodling (a sketchbook prop);
  - napping (the pillow/blanket prop, sleepy idle; favoured late at night);
  - tidying her clutter (the WP-21 tidy routine);
  - looking out at the screen / stretching.
- Hobbies last 5–20 min with transitions between them. Source any missing
  clips (reading/sitting idles) per WP-18's source list (not Mixamo), or via
  felt-t2a-studio.
- Report each hobby as a diary event. On `afk_end`, after a long absence, she
  sometimes mentions it ("finished two chapters while you were gone. it was
  mid.") through the normal budget.
- No screen sampling while AFK (it's pointless and costs quota).

**Accept**: leave the PC for 15+ min; on return she's visibly mid-hobby, and
the diary mentions it the next day.

---

## WP-31

### Calendar heads-up
**Repo**: felt-core (deploy). **Size**: S. **Depends on**: WP-25.

**Do**:
- A background task in felt-core polls Google Calendar (the existing
  `google_calendar.py` client) every 5 min for the next 2 h.
- For each event, enqueue (WP-25) a proactive heads-up at **T−30 min** (normal)
  and **T−10 min** (`urgent`, delivered even while she's hidden or away).
  Phrased through the cloud (calendar is `google_ok`) with the tone line, and
  aware of context when available ("you're mid-match, but dentist in 10").
- Don't repeat for the same event; skip all-day events (or give them a
  morning mention only); respect deletions and moves (re-check before
  delivery, with a short expiry).
- `set_alarm`-style explicit alarms stay as they are. This is only a gentle
  heads-up.

**Accept**: a test event 12 min out produces the 10-min heads-up on time
(spoken plus a bubble), including while she's "away".
