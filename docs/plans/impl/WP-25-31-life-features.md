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

### Live accept test (2026-09-27) ✅
- The test queued one live line from inside the felt-core container with
  `enqueue_proactive()`. It didn't use FELT_DEBUG, which stays off in prod
  (`/v1/proactive/debug` → 404 verified).
- felt-tray claimed it **0.4 s** after the enqueue. The already-expired item
  was never delivered (`delivered_at` NULL).
- The felt-tray log shows the full chain: `/next` 200 → `/audio` 200 (+2.1 s)
  → felt-animation `/reply_ready` 200. That's about 3 s end to end; almost
  all of it is on-demand TTS.
- **Fix: felt-core `db0b5cb`.** Audio is pre-synthesised at enqueue time
  (when enqueued inside the server loop, which is how WP-26/WP-31 will
  call it). A `/audio` fetch mid-synthesis joins the same task.
- A 422 on a malformed debug body only reveals that the route exists.
  Harmless.

### Notes from implementation (🔎 needs review, 2026-09-27)

**felt-core** (`src/felt_core/`):
- `db.py`: `proactive` table exactly as specced (`id, kind, text,
  payload_json, created_at, expires_at, delivered_at`) — `animation_tag`/
  `emotion` live inside `payload_json`, not extra columns, since the WP
  spec's table listing is exactly those six. Helpers:
  `insert_proactive`, `claim_next_proactive` (atomic select+mark-delivered
  in one transaction, excludes expired rows so an expired item is
  structurally unreachable, not just filtered by a caller),
  `get_proactive_item`, `requeue_proactive` (clears `delivered_at` only if
  not expired), `prune_expired_proactive` (called at startup, same
  convention as `delete_old_latency_rows`).
- `proactive.py` (new module): `enqueue_proactive(config, kind, text, *,
  animation_tag=None, emotion=None, ttl_s=600)` — the one function WP-26/
  WP-31 should call; `wait_for_next(config, timeout_s)` — the long-poll,
  polling `claim_next_proactive` every 0.5 s. **Deviation from the spec's
  "async wait with a small internal poll/asyncio.Event"**: implemented as
  plain `asyncio.sleep`-paced polling, no `asyncio.Event`. A module-level
  `asyncio.Event` binds to whichever event loop first waits on it, and
  felt-core's own test suite (a fresh loop per async test) hit "Event is
  bound to a different event loop" immediately — not worth a per-loop
  lazy-Event workaround for a 0.5 s worst-case wakeup delay in a
  single-process app. `clamp_timeout` bounds `?timeout=` to 1–30 s.
- `api.py`: `GET /v1/proactive/next?timeout=` (204 on timeout, JSON
  `{id, kind, text, animation_tag, emotion}` otherwise), `GET
  /v1/proactive/{id}/audio` (reuses `tts_cache`/`strip_for_tts` exactly
  like `_synthesize_reply`, just returning the bare WAV with no X-*
  headers), `POST /v1/proactive/{id}/requeue` (`{"requeued": bool}`),
  `POST /v1/proactive/debug` (404 when `FELT_DEBUG` isn't set — not a 403,
  so the route's existence isn't discoverable either way). `/next` was
  added to `_UNTIMED_PATHS` (a 30 s-capped long-poll would otherwise swamp
  the `total` stage's percentiles, same reasoning as `/v1/music/now`).
  Auth: none — same LAN-only, no-auth posture as every other `/v1/*`
  route (see `api.py`'s own CORS comment).
- `config.py`/`.env.example`: `debug: bool = False` / `FELT_DEBUG=`.

**felt-tray** (`src/felt_tray/`):
- `api_client.py`: `FeltCoreClient.get_proactive_next(timeout)` (None on
  204, HTTP timeout padded `+10s` past the server-side long-poll so an
  honest slow 204 isn't mistaken for a network failure),
  `get_proactive_audio(item_id)`, `requeue_proactive_item(item_id)`.
- `proactive_poller.py` (new module): `ProactivePoller` — a daemon thread
  long-polling `get_proactive_next` in a loop. On an item: if
  `not is_visible() and kind != "urgent"`, requeues it and idles 10 s
  (`_HIDDEN_PAUSE_S`) before polling again (avoids a hot requeue loop
  while Felt stays hidden); otherwise fetches audio and calls the
  `deliver` callback. A `get_proactive_next`/`get_proactive_audio` failure
  backs off 5 s → 60 s (doubling each miss, reset to 5 s on any success,
  including a clean timeout). `tick()` is split out from the thread loop
  so tests drive it directly with a fake client, no real thread/sleep.
- `app.py`: `App._on_proactive_item(item, audio)` — the poller's `deliver`
  callback, toasts the text (if any) and calls the existing
  `_deliver_reply(text, animation_tag, audio, prompted=False,
  emotion=...)`, the exact same felt-animation `/reply_ready` path a
  screen reaction uses, so hush/ducking/bubble/cooldown all apply
  desktop-side unchanged. Poller is built in `_build_proactive_poller()`
  and started in `run()` only when `config.proactive_poll_enabled`
  (default on); stopped in `quit()`.
- `config.py`/`.env.example`: `proactive_poll_enabled: bool`,
  `FELT_PROACTIVE_POLL_ENABLED=1` (off via `0`/`false`).

**Tests**: felt-core — `tests/test_db_proactive.py` (10, db helpers) +
`tests/test_proactive.py` (17, enqueue/wait_for_next/clamp_timeout +
all 4 endpoints incl. debug 404/200 and 204-on-timeout with a 1 s
timeout) — 423 passed total, `ruff check`/`ruff format --check`/`ty
check` all clean. felt-tray — `tests/test_proactive_poller.py` (11,
visible/hidden/urgent/backoff/audio-failure/exception-safety) +
`tests/test_api_client.py` additions (5) + `tests/test_app_delivery.py`
additions (2, `_on_proactive_item` wiring) + `tests/test_config_proactive.py`
(4) — 174 passed total, `ruff`/`ty` clean.

**Not done / unverified**: this is unit/smoke-tested only, not
live-verified against a real deployed felt-core + running felt-tray/
felt-animation (rule 27) — Mario needs to run the accept test himself
once felt-core deploys with `FELT_DEBUG=1`:
```
curl -X POST http://192.168.1.110:8420/v1/proactive/debug ^
  -H "Content-Type: application/json" ^
  -d "{\"kind\": \"diary\", \"text\": \"hey, missed you\"}"
```
(PowerShell; a plain `curl.exe`/WSL bash quoting works too) and confirm
Felt speaks it within ~2 s. Also unverified live: the hidden/away requeue
behavior (needs Felt actually hidden during a real proactive push) and
the 404 posture for `/v1/proactive/debug` on the real deployment (depends
on `FELT_DEBUG` staying unset in prod `secrets.env`/compose env, which
this WP did not touch).

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

### Combined with personality plan P4, self-memory (Mario, 2026-09-27)
Mario asked to do WP-26 "along with the personality change since she will
have memories on that side too". One nightly pass reads one set of
cloud-safe material and writes both halves:
- **Diary** (her record of *their* day): `entry`, `callbacks`, `mood_word`,
  exactly as above.
- **Self-memory** (what *she* takes away): `self_updates` in the same JSON
  call. Each is `{kind: opinion|like|dislike|running_joke|grudge,
  text, confidence}`, e.g. "decided the Factorio trains are 'her'
  trains", or a running joke about the same boss.
  - Stored in `self_memory(id, kind, text, source_date, uses, last_used,
    status: active|retired|vetoed, pinned, edited)`.
- **How it reaches her prompt:**
  - `persona.yaml`, Mario-authored, stays the fixed core.
  - A compiled "who you've become" block of ≤ ~8 active self-memories,
    most relevant first, keyword-matched to what's on screen (the
    SillyTavern lorebook idea), each with a use count and cooldown.
  - The diary's "Recently" snippet.
  - Everything together is capped at ~200 tokens on top of the sheet
    (Gemma's free tier is 16K TPM).
- **Guardrails:**
  - A self-memory can't contradict `persona.yaml`. The writing prompt gets
    the sheet and must not overwrite core traits.
  - At most ~30 active; the oldest unused ones retire.
  - Nothing from facts or unsafe chat.
- **UI deferred** (Mario, 2026-09-28: "dont make the dashboard yet, thats
  a later feature"). WP-26 ships the API only; the pages belong to
  **WP-42 (Felt app)**. When built, Mario controls both there: the diary list plus edit/delete, and the self-memory list plus
  pin, edit, veto and delete. A vetoed item is never re-added. Its text goes
  into the writer's "don't" list.
- **Morning greeting:** `enqueue_proactive` inside the server loop, so the
  audio is pre-synthesised. It's written in her persona voice and may use a
  callback or a fresh self-memory.

### Build notes (🔎 awaiting the first real morning, 2026-09-28)
- **felt-core `8143725` (deployed):**
  - `POST /v1/events`; the `diary`/`diary_weeks`/`self_memory` tables;
  - `diary.py` (material gatherer + writer);
  - `self_memory.py` (upsert/dedupe/veto/≤30 cap + `memory_block`, wired
    into `personality_prompt` for replies, screen and event reactions);
  - the diary and self-memory API; the `diary_recall` skill (public).
  - A Sonnet agent built it; a session limit cut it off before its checks. I
    finished it: 1 test with near-duplicate data, 10 ty errors in tests, 1
    lint finding.
- **Review fix:** the writer ran inline in `/v1/events`, but felt-animation
  posts with a 2 s timeout and buffers/retries, so a retried day_start
  could start a second write (two cloud calls, two greetings). It now runs as
  a FastAPI background task after the 204, with a per-date in-progress
  guard. There's a test for it.
- **Test fix:** `test_metrics` slept 10 ms and asserted ms > 0. Windows'
  ~15.6 ms monotonic tick made it order-dependent. It now sleeps 50 ms.
- **felt-animation `96f6eaf` + `483f210`:** event reporting (games+duration,
  afk, day_start once per date after 05:00, hourly mood, hush, window_fall,
  ledge_sit, prop_used), buffered across outages. **The music_track poll was
  removed.** It hit `/v1/music/now` (a live Spotify call per request) every
  15 s on top of felt-tray's poll, and felt-core already keeps listening
  history for the diary.
- The dashboard UI is deferred to WP-42.
- **Next:** restart Felt so felt-animation reports events. The first entry
  is written on the first activity after 05:00; then check the morning
  greeting and `GET /v1/diary`.

**Tests**: material selection excludes unsafe chat windows and facts;
callback decay; the weekly compression trigger; prompt snippet length.

**Accept**: after a real day of use, the next morning she greets Mario with a
line that clearly references yesterday. `GET /v1/diary?date=` shows a sensible
entry. The prompt snippet shows up in chat/screen calls (check the logs at
DEBUG).

---

## WP-27


> **Decided 2026-09-26 (Mario, during WP-21):** sunny weather → put her in the **summer outfit for a while** (instead of sunglasses, which were dropped as "very off"). Pick which outfit VRM counts as summer with Mario.
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

### Parked for polish (2026-09-30): generated mix-and-match outfits

Mario: "park it, leave it to polish". Tier C (16 VRoid outfits) and 10
Tier-A recolour variants are live. What exists for the polish pass:

- **Pipeline (umbrella `tools/outfits/`):**
  - `name_parts.py`: a watcher that auto-names VRoid part exports.
  - `combine.py`: splices garments onto a base.
  - `patterns.py`: styles fabric per garment.
  - `design_styles.py`: Felt designs 3 looks per piece.
  - `tag_pieces.py`, `fit.py` (the geometric poke check) and `make_sets.py`.
  - `render_sets.py` and `felt_pass.py` (Felt ranks sets in groups of four).
  - `build_review.py` and the review app `tools/outfits/review/`.
- **Data:**
  - 98 named pieces in `E:\Felt\Model\OutfitBuilderNamed\`, with their
    catalog, `styles.json`, `tags.json` and `fit.json`;
  - 144 sets and their renders in `E:\Felt\review\wardrobe-sets\`.
- **Learned the hard way:**
  1. **Feet: shoe exports must be the base.** Every VRoid shoe export raises
     her skeleton by 1.4 to 4.5 cm and reposes and re-meshes the feet.
     Splicing a shoe onto the flat-footed undies base mangles the feet as
     soon as the mesh is skinned. Static pyrender renders never skin, so
     they hid it. Fix, verified in the three-vrm viewer: base = the shoe
     export itself (undies + shoe, right skeleton and feet), with the other
     garments spliced on. Still to build into `combine.py`:
     - restyling the base's own shoe material;
     - painting socks relative to the plain undies' skin texture, not the
       shoe base's.
  2. **Styling per piece, then mixing by rules, gives incoherent outfits.**
     Mario's review: patterns on shoes and socks, matching camo or gradient
     twins, a grey fancy top + skirt + fishnets, 9/15 dresses. Next approach:
     style at the outfit level, where Felt composes whole outfits from the
     catalog with one palette, and hard rules apply: at most one patterned
     piece, solid shoes, socks solid or striped. Try a batch of ~20 before
     scaling.
  3. **Felt rating outfits one at a time isn't a filter** (98/98 "wear",
     95 of them 8/10). Ranking in groups of four works.
  4. For WP-28 (lighting), check skinning-sensitive things in the animated
     viewer, not in bind-pose renders: the review app's `?item=&view=feet`
     plus headless Edge with its own `--user-data-dir`.

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
the scene's tint without looking odd; the blob shadow grounds her; ~~with a
browser behind her, the lighting goes neutral~~ (dropped 2026-09-30: Felt is fully local,
Mario loosened the filter; the sampling never leaves felt-tray anyway).

**Built 2026-09-30.** felt-tray `ambient.py` (her box from felt-animation `GET
/ambient/char_rect`, grown 50 %, one HALFTONE StretchBlt to 64x64, her box
masked, average / dominant bright / luminance, sent on change) ->
felt-animation `POST /ambient_light` -> overlay `{"ambient_light"}`. The
overlay reports `{"char_rect"}` every 0.5 s while she moves. The shadow is a
camera-facing ellipse on her floor line behind her feet: the views are
straight-on orthographic, so a floor decal would be edge-on and invisible.
Only its top half shows at the monitor's bottom edge. Knobs:
`FELT_AMBIENT_LIGHT_ENABLED`, `FELT_AMBIENT_LIGHT_S`; in main.gd `AMB_*`,
`SHADOW_ALPHA`, `SHADOW_HEIGHT_M`.

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

**Built 2026-09-30** (felt-core `685fdf8`, infra `f406355`), adapted to fully local:
- **The exe** is `pathofexilesteam.exe` (1000+ reactions already logged).
- **Screen reactions:** `brain/poe_reactions.py` gives any `pathofexile*`
  app a PoE-aware instruction and schema, which adds `items: [{name, kind}]`.
  Up to 2 unique/currency items are priced with `poe_price_check`, called
  directly; unique names are snapped to the trade cache with difflib. Then
  one short felt-llm call writes her line with the price. So a normal
  reaction is one call, a priced one two. Normal cooldown.
- **Wiki:** the `poe2_wiki` skill calls poe2-rag's new `/api/search`
  (retrieval only), because `/api/ask` answers with cloud Gemini through
  ninerouter. The passages go to felt-llm like any other tool result. No
  router examples are needed any more: one call with native tools
  (WP-36), and the skill description steers it away from web_search.
- **Needs Mario's live check:** hover a unique or currency tooltip in PoE2
  (cooldown permitting), and ask her a mechanic question.

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

**Notes from implementation (2026-10-01):**
- felt-animation `754ec1d`: `hobbies.py` director. After 10 min idle she
  picks a hobby every 5–20 min (never the same twice): reading (book, seated
  idle), handheld gaming (controller), napping (blanket + pillow, eyes closed,
  weighted up late at night / low energy), tidying (only with clutter),
  stretching / looking around. On return she's caught mid-hobby, puts props
  away and stands. The hobby goes to the diary and the welcome-back event.
  Stray book removed from the `afk_start` reaction.
- felt-core `30bba1e`: first-person diary line + optional hobby mention in
  the welcome-back line (whitelisted hobby names only).
- felt-tray `aaebcd6`: periodic screen captures skipped after 10 min without
  input (`GetLastInputInfo`); focus change / Look still capture.
- **Not deployed server-side:** felt-core CI built the image, but its tag
  bump still pushes to `192.168.1.110` (Actions secrets `INFRA_REPO_URL` /
  `INFRA_KNOWN_HOSTS` need updating, values in the WP-29 session); the manual
  promote is waiting for Mario.
- **Gap:** no real reading / lying-down clips and no sketchbook prop, so
  reading uses the seated idle and doodling is left out (POLISH-BACKLOG).
- Live: first launch after the change logged `hobbies: stretching for 18 min`
  while Mario was out.

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

**Notes from implementation (2026-10-01):**
- felt-core `e5ddf11` (local only, not pushed): `calendar_headsup.py`, a
  lifespan loop (off when Calendar isn't connected). It polls all calendars
  every 5 min for the next 2 h and gives each stage its own timer, so T−10
  is on time rather than up to 5 min late. A late first sighting (8 min out)
  sends only the urgent one.
- Re-fetches the event (`google_calendar.get_event`) right before phrasing:
  deleted/cancelled → dropped; moved → dropped, and the next poll
  reschedules it under a new key (dedupe = event id + start + stage, kept in
  `settings`, so restarts don't repeat).
- Skips all-day events (no morning mention yet) and events Mario declined.
- Phrased by her local model (WP-36: no cloud), with game context from the
  WP-26 event log (unstopped `game_start` → "he's in the middle of X"). Plain
  "heads up, X in N minutes." if felt-llm is down.
- Expiry: urgent expires at event start; the 30-min one after 15 min.
- **Accept check still to do** after deploy: test event 12 min out → the
  30-min line now, the urgent one 2 min later, also while she's away.

### WP-27 build spec (2026-09-30): Tier-C VRM outfits

**Mario's decisions (2026-09-30):**
- **Halloween:** 31 October only.
- **Christmas:** 23–26 December, with **Xmas** and **Reindeer** on
  alternate days.
- **Gaming:** she keeps her normal (daily) outfit.
- **Rare themed pool:** China, Maid, Cyberpunk, Cyberpunk2.
- **Daily random pool:** General 1–4, LaceDress, NightOuting, Sport and the
  default `felt.vrm`, which is the only one that gets the WP-33 daily tee.
- **Ambient:** now and then she changes into anything; themed outfits are
  rare.
- **Night:** pyjamas when it's properly late (past ~01:00, the same "late"
  rule as her bedtime nags) or when her mood is sleepy. Back to the day's
  outfit after 05:00.
- **Bikini:** **only** as a reaction to Mario asking about the weather when
  the answer is sunny, at a **1 % chance**. It is not the summer default.
  - Mario: "do bikini only for whats the weather -> sunny and do that like
    the mega rare 1% chance".
- **The VRMs are full models**, exported like the original `felt.vrm`, in
  `felt-godot-overlay/characters/Felt_*.vrm`.
  - **They are not committed to git** until Mario says which are free to
    push; some come from Booth packs.

**Measured (glTF inspection):**
- All 16 outfits have the same 52 `J_Bip_*` humanoid bones with identical
  rest rotations. Only the hips' rest height differs, which is the shoe
  height: −1.4 to +4.9 cm, absorbed by `_clamp_feet_to_floor`.
- Meshes are merged (`Face (merged)`, `Body (merged)`, `Hair001 (merged)`),
  and each adds 8–109 clothing spring bones.
- **So an outfit change = swap the whole character scene and reuse the
  retargeted `AnimationLibrary`.** There is no re-retargeting.

**Relay contract (felt-animation → main.gd):**
`{"outfit": {"id": "maid", "vrm": "res://characters/Felt_Maid.vrm", "fx": "puff"|"none"}}`.
- main.gd swaps the model, keeping the pivot (position/facing), the current
  tag and the props held on bones. It re-runs every per-model setup:
  animation tree, pose modifier, feet clamp, face/blink/mouth caches, MToon
  tuning, collider radii, and the props' skeleton.
- It replies `{"outfit_applied": {"id": ...}}` when done, or
  `{"outfit_failed": {"id", "error"}}`.
- `"fx": "puff"` plays the prop puff at her position during the swap.

**felt-animation decides:**
- `outfits.json`: id, vrm, pool (`daily` / `themed` / `special`), triggers.
- The wardrobe state persists (the current outfit plus the day's pick), so a
  restart re-sends the current outfit on overlay connect.
- **Change styles** (choreography by felt-animation):
  - **Quick:** a spin/twirl clip, with the outfit message sent mid-clip.
  - **Proper:** a walk off-screen ("brb, changing"), the swap while she's
    hidden, then back.
  - Night pyjamas and the date outfits use **proper**; ambient changes and
    the bikini use **quick**.
- A debug endpoint `POST /outfit {"id": ...}` forces a change, for testing
  and a later tray menu.

**Status 2026-09-30: Tier C accepted.**
- felt-animation `3f71524` (outfits.json, `outfits.py`, `/outfit`) and
  overlay `5724dd7` (the whole-model swap).
- Live: Halloween (the tallest heels, +4.9 cm) and Maid swapped with feet on
  the floor, and animations, hair, cloth and lipsync were all normal.
- Mario: "yes on floor, everything normal, animations etc look great. Just
  swapped to maid, all perfect there too".
- **Left:**
  - **Tier A:** recolour variants on top of these outfits.
  - **Say which outfit VRMs may be committed:** some come from Booth packs,
    so none are in git yet.
  - **Optional:** a "brb, changing" line for proper changes (it's a silent
    walk-off now).

**WP-29 v2, 2026-10-01/02: price checks via Exiled Exchange 2's key.**
Vision failed the live check. The tray sends 768 px frames, which is too
small to read tooltip names (Mario: "she pointed how much text it is, but
not the price"). Mario chose to keep **EE2 stock and auto-updating** ("can
we have EE2 its own thing, and have her learn pricing on the side"): no
fork, because leagues bring frequent EE2 updates.
- felt-tray `poe_clipboard.py` (`110e590`): polls the clipboard *sequence
  number* and reads the contents only when it changes while a PoE window is
  in front. It only accepts the game's `Item Class:` / `Rarity:` format;
  anything else is dropped unread. EE2's "restore clipboard" is off on
  Mario's box, so the item text stays put.
- felt-animation `POST /poe/item` (`7549e67`): 10 s repeat guard, a silent
  `poe_item_checked` event-log entry (the WP-57 learning data), then event
  `poe_item` to felt-core.
- felt-core (`ed26493`, `76855d4`): `parse_item_text`, uniques and currency
  priced with `poe_price_check`. She only speaks with a real price and stays
  silent otherwise (rares: EE2's widget prices those by mods).
- Verified end to end on 10-02 with a Divine Orb text: priced "~1.00 divine
  (league: Forbidden Rites)", spoken line, event logged.
- Left: Mario presses EE2's key on a real unique in game.
