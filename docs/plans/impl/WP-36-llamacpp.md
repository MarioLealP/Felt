# WP-36 — Replace Ollama with self-managed llama.cpp (`llama-server` router mode)

Read `00-implementer-context.md` first. **Repos:** felt-core (server, so
deploy), felt-animation, felt-tray, felt-vision (retired), umbrella
(`tools/felt-llm/`, `LaunchFelt.ps1`, `tools/sounds/nitro/orpheus_gen.py`).
**Machines:** Nitro5 (new service), desktop (Ollama removed).
**Size:** M–L. **Depends on:** nothing. Do it before WP-34, which must then
package the result instead of Ollama.

Mario, 2026-09-26: "Can't we swap out of the sketchy ollama? and do that
management ourselves?" and "I'm fairly sure model max count and stuff like
that can be handled by llamacpp." **He's right:** llama.cpp's own router
mode covers it (see *Why*, point 3). No llama-swap, no custom supervisor.

Everything below was measured read-only on 2026-09-26. Nothing was changed.

---

## ⚡ Revision 2 (2026-09-29): host it on the server's P104, not the Nitro5

The P104-100 (8 GiB, Pascal sm_61) is now installed in the server and
passed its burn-in (see `runbooks/clockmost-infra.md` → GPU). That changes
**where** this WP runs and **what models** it serves. The *why* below
(Ollama is fragile, router mode covers model management) and the caller
inventory still hold. Steps 0 and 3 (Nitro5 install, VRAM sharing with
felt-voice) and the Nitro5 resource plan are **superseded** by this
section. Steps 1, 2, 4, 6 and 7 still apply, retargeted at the server.

Mario, 2026-09-29: "don't just move, lets do a proper plan, and check what
we can improve / change, … newer models so we are up to date".

### Why the server is better than the Nitro5

- **It's always on.** The Nitro5 reboots most days and is off whenever
  Mario isn't using voice. felt-core's local paths (router, privacy,
  private chat) fail whenever it's off. felt-core's logs show connect
  timeouts to `192.168.1.104:11434` today.
- **It's the same box as felt-core.** Calls go over the Docker network,
  and the models sit on local disk (`/home/ai-models/gguf`), with no NFS
  automount (the root cause of 09-26's outage).
- **The whole 8 GiB is ours.** Nothing else uses the P104, so there's no
  sharing with felt-voice or ComfyUI. The Nitro5 keeps felt-voice (TTS)
  and ComfyUI, and gets its full 6 GB back.
- **TTS stays on the Nitro5.** Research (Gemini, 2026-09-29, unsourced
  but consistent with PyTorch's release notes): PyTorch's cu128+ wheels
  dropped sm_61, and Chatterbox/RVC in fp32 on Pascal would run about
  3–5× slower than the 3060. Not worth it.

### Model research (2026-09-29)

Gemini did a web-search pass (`agy`, gemini-3.1-pro). I verified every
name against the Hugging Face API, because its report cited only org
pages, missed half the recent releases, and got two facts wrong: "Ollama
depends on PyTorch" is false, and "llama.cpp must be compiled from source
for sm_61" is disproved by our own bench on the official image.

**Current generation, fits 8 GiB, llama.cpp-supported, Apache-2.0:**

| Model | Released | GGUF used | Weights + mmproj | Notes |
|---|---|---|---|---|
| Qwen3.5-9B | 2026-02 | unsloth Q4_K_M | 5.68 + 0.92 GB | natively multimodal; hybrid Gated-DeltaNet attention (small KV) |
| Qwen3.5-4B | 2026-02 | unsloth Q6_K | 3.53 + 0.67 GB | same family |
| Gemma 4 E4B | 2026-03 (QAT GGUF 2026-05) | google QAT q4_0 | 5.15 + 0.99 GB file, **4.2 GB VRAM** | image + audio input; per-layer embeddings |
| Qwen3.5-0.8B | 2026-02 | unsloth Q8_0 | 0.81 GB | classifier candidate; not needed (below) |

**Checked and rejected:**
- **Too big for 8 GiB with any context:** Gemma 4 12B (QAT q4_0 is
  6.98 GB), Qwen3.6/3.8 (27B+, and Qwen3.8-Flash-Next is 125B total),
  Granite 4.2 30B.
- **MoE with CPU offload** (Qwen3.6-35B-A3B class): needs ~20 GB, and the
  host has 14 GiB and is already memory-pressured.
- **Granite 4.2 8B** (2026-08, Q4_K_M 5.35 GB): text-only, business-tuned.
  A fallback if the Qwen/Gemma picks disappoint.
- **LFM2.5-VL-3B** (2026-08): a small VLM, a fallback for vision only.
- Anything older (qwen2.5, llama3.1, the Ollama blobs we hold): a
  generation behind.

### Feasibility bench on the P104 (2026-09-29, measured)

**Setup:**
- official `ghcr.io/ggml-org/llama.cpp:server-cuda` (build 11243, v0.5.0),
  **unmodified — sm_61 kernels included**
- `-ngl 99 -c 8192 -np 1`, thinking off (`chat_template_kwargs.enable_thinking=false`)
- 120 W cap
- **Prompts:** her real compiled persona (≈1.4K tokens), 4 chat lines, her
  real screen-reaction instruction, and her real privacy prompt with 8
  labelled cases.
- **Images:** 2 synthetic 1600×900 screenshots. One is a VS Code Godot
  parse error at 02:47; the other is a Teto YouTube page.
- **Files:** script `/home/ai-models/gguf/bench.py` + `runbench.sh`, raw
  output `bench-*.json` next to them.

| | Qwen3.5-9B Q4_K_M | Qwen3.5-4B Q6_K | Gemma 4 E4B QAT |
|---|---|---|---|
| VRAM (ctx 8K, + mmproj) | 6.6 GiB | 4.8 GiB | **4.5 GiB** |
| Generation | 27.8 tok/s | 34.0 tok/s | **43.2 tok/s** |
| Prompt processing | 160 tok/s | 290 tok/s | **390 tok/s** |
| Chat, first turn (cold persona) | 11.8 s | 8.7 s | **4.5 s** |
| Chat, warm (persona cached) | 1.2–6 s (rambles to the 160 cap) | 2.5–4 s (rambles) | **0.5–0.8 s** |
| Screen reaction from the image | 10–12 s | 7–9 s | **3.8–5.4 s** |
| Read the screenshot correctly | ✅ both | ✅ both | ✅ both (misread `seat_y` as "seat") |
| Privacy classifier | 8/8, 0.37 s | 8/8, 0.34 s | 8/8, **0.15 s** |
| Character (my read) | most "her": teasing, bread, "my sit animation", but long and **invents specifics** ("that script from last week") | rambles, invents | short spoken-length lines, **doesn't invent** ("which song?"), but blander |

**For comparison:** today's cloud screen reaction is **p50 31 s, p95 55 s,
max 62 s** (Gemma 4 26B free tier, n=70, `/v1/metrics/latency`).

**Findings:**
1. **Local vision is now viable and much faster than the cloud.** It also
   keeps screenshots on the LAN. Today every screenshot goes to Google.
2. **A single GPU model can do every job** (chat, privacy, router, vision,
   diary), so a separate classifier model isn't needed. Every candidate
   got 8/8 at ≤0.4 s. One model means one CUDA context, no eviction
   juggling, and `--models-max 1` on the GPU.
3. **Persona prefix caching is what matters.** Warm is 10–20× faster than
   cold, so the warm-up loop (step 2) is essential. The multimodal calls
   re-evaluated the whole persona each time (`prompt_n` 1525 vs 63 for
   text), which is worth tuning (image placed after a cached text prefix,
   `--cache-reuse`) before judging vision latency.
4. **The bench isn't the eval.** It lacks felt-core's post-history
   instruction and length rules, so "rambles" and "invents" may largely
   disappear in the real prompt. The real pick comes from
   `evals/persona_eval.py` (Phase B).

### Revised phases

**A. `felt-llm` stack on the server** (clockmost-infra `projects/felt-llm/`)
- compose:
  - the official image **pinned by tag + digest** (≥ b11146; bench used
    11243)
  - `devices: [nvidia.com/gpu=all]`
  - router mode with a preset INI; `/home/ai-models/gguf:/models:ro`
  - `mem_limit`; `restart: unless-stopped`
- **Network:**
  - joins a `felt` network shared with felt-core. felt-core calls
    `http://felt-llm:8080`.
  - LAN port published only for the desktop's reaction picker (step 4),
    scoped by the host firewall to the desktop like felt-core's 8420,
    with `--api-key-file`.
  - no Caddy/public route
- **Preset:**
  - one GPU model with `np 3` (chat, router, privacy each keep their own
    warm slot)
  - `c` sized per slot for the 3.8K router prompt
  - `cache-ram` capped (the default is 8 GiB, and the host has 14)
  - no flags that are already defaults
- **Monitoring:** GPU temperature/power into the existing Zabbix, plus an
  ntfy alert on the container going unhealthy.
- **The 120 W cap stays** until the memory thermal pads are replaced.
  Felt's load is bursty (~45 W measured while generating).
- **Model files:** `manifest.toml` (the name, HF repo, file and SHA-256
  for each GGUF) + an idempotent `fetch.sh`, committed in the umbrella's
  `tools/felt-llm/` (WP-34 reuses them).

**B. Bake-off with the real prompts**
- `persona_eval.py` gains a `local:<model>` arm pointed at felt-llm.
  Candidates: Gemma 4 E4B, Qwen3.5-9B, Qwen3.5-4B, and the current cloud
  model as reference.
- Its metrics (hype/agree rate, distinct-2, repeated trigrams) plus the
  **blind A/B HTML for Mario**, who picks by taste.
- **Router parity:** replay 50 recent real messages through the router
  with a JSON-schema `enum` of the skill names. ≥ 48/50 must match cloud
  or the current router.
- **Privacy:** a 40-case labelled set (the 8 above + real-shaped cases).
  Fails closed.
- **Vision:** 10 synthetic screenshots of Mario's real apps (PoE2,
  Factorio, VS Code, YouTube, Discord, FFXIV). Did she read it right, is
  the line in character, and how long did it take.

**C. felt-core port** (step 1 + step 2 as written, retargeted)
- `local_llm.py` with per-caller backend flags
- router date line moved to the end
- warm-up loop
- metrics with `cache_n`

**D. Switch-over**
- Flip router and privacy first, then chat.
- Then remove Ollama on the Nitro5 (step 7) and point felt-voice's docs
  at the full 6 GB.

**E. Local screen reactions.** Mario's decision, see below.

**F. Desktop** (steps 4, 5, 7 as written)
- the reaction picker moves to felt-llm
- the desktop's Ollama and felt-vision are removed
- `LaunchFelt.ps1` is cleaned up

### Improvements this unlocks (later, not in this WP)

- **A private diary.** WP-26's writer only sees cloud-safe material. A
  local writer could also read the private chat and facts. It's a
  nightly batch, so latency doesn't matter.
- **Gemma 4 takes audio input,** a possible future path for STT or tone.
  Not now.
- **Local embeddings** for memory recall, if keyword recall stops being
  enough.

### Decisions (settled 2026-09-29)

1. **Local-first, everywhere quality holds.**
   - Mario: "Sounds good" (local screen reactions), then "at the end of
     the day the more we can do local the better".
   - The cloud stays only for what is inherently external (web search,
     research) and as a fallback when the P104 is down.
2. **Model: Gemma 4 12B QAT q4_0** (+ its 0.18 GB mmproj), chosen by
   Mario's blind A/B (3 rounds, below).

### Blind A/B (2026-09-29)

**Setup:**
- 2 messages per arm, then 2, then 3; letters reshuffled each round;
  Mario ranked the replies.
- Every arm got the production prompt from `personality_prompt` (persona
  + memory block + tone).
- Rounds 2 and 3 add "Reply out loud in one to three short spoken
  sentences."

| Round | cloud (flash-lite) | Gemma 4 12B | Qwen3.5-9B | Gemma 4 E4B | Qwen3.5-4B |
|---|---|---|---|---|---|
| 1 (map / walk) | 1, 1 | — | 2, 3 | 3, 2 | 4, 4 |
| 2 (boring; rice: "don't like any") | 2 | 3 | 1 | 4 ("goes off on its own") | — |
| 3 (rice / project / desktop, **new persona**) | 3, 2, 2 | **1, 1, 1** | 2, 3, 3 | — | — |

**Round 2 exposed three persona bugs,** which every model showed, the
cloud included. The fix is felt-core `ad0c221`.
- **The quoted pet phrases became a script.** Mario, on Gemma 12B: "it
  goes im choosing to be supportive about *".
- **Bread became a reflex:** every food message turned into "baguette
  wins".
- **The diary block was recited word for word** ("digital surgeon… sleepy
  Nitro machine", "red rocks"). WP-26 had already written its first entry
  on 09-28, and the block was presented as bare text. It's now framed as
  background, not to be quoted.

After the fix the catchphrase count dropped from 2 to 0, and the 12B won
every item in round 3.

### The 12B on the P104: one slot, one call (measured 2026-09-29)

**What fits:**
- 7.9 GiB at `-c 8192 -np 1 -ub 1024 -ctk q8_0 -ctv q8_0` (`-ub 1024`
  is required: the image chunk asserts `n_ubatch >= n_tokens` at the
  default 512).
- `-c 16384 -np 2` and `-np 3` both run out of memory.

**Speed:** 20 tok/s generation, ~120 tok/s prompt. Screen reactions from
the image take 6–7 s.

**Classifiers, measured on 18 real-prompt routing cases and 16 privacy
cases:**

| | Router | Privacy | Router warm | Privacy warm |
|---|---|---|---|---|
| Gemma 12B (GPU) | **18/18** | **16/16** | 1.0–2.1 s | 0.9 s |
| Qwen3.5-0.8B (CPU) | 13/18 | 14/16: salary and therapist leaked as SAFE | 0.3–1 s | 0.2 s |
| Qwen3.5-2B (CPU) | 13/18 | 13/16: the server IP leaked | 0.5–1.3 s | 0.4 s |

The small CPU models are **rejected**: a privacy classifier that leaks is
worse than none.

**Three prompts in one slot doesn't work here.** Privacy, router and
persona are three different prefixes.
- `--cache-ram` does restore them, but Gemma's cache entries are
  0.5–0.9 GB each and a restore over PCIe Gen1 x4 takes ~2 s.
- An interleaved turn took **9–23 s**, and a cold 4.1K-token router
  prompt took 17 s.

**What works: one call with native tool calling.**
- The persona is the system prompt, the skills are OpenAI `tools`, and
  llama-server runs with `--jinja`.
- **18/18** on the same routing cases.
- Tool turns take 1.1–2 s and pick sensible arguments ("Kasane Teto",
  "desk lamp, off", "Divine Orb").
- Chat turns answer in character in 3–4 s (80-token cap).
- It's one prefix, so it stays warm.
- Script: `/home/ai-models/gguf/toolcall.py`.

### Revised design (supersedes phases C/D above where they conflict)

**One GPU model does everything:**
- `felt-llm` serves Gemma 4 12B and nothing else on the GPU:
  `--models-max 1`, `load-on-startup`, never evicted.
- A chat turn is one `/v1/chat/completions` call carrying the persona,
  the memory block, history and every skill as a `tools` entry.
- A tool call runs the skill, and the result goes back as a `tool`
  message for the spoken phrasing: a second call on the same warm
  prefix.
- The 2026-09-11 finding that "the chat model is unreliable at tools
  under a mixed prompt" was about qwen2.5:3b, and doesn't hold for
  Gemma 4 12B (18/18).

**`router.py` and the local privacy call retire from the chat path:**
- The separate router call goes. Its hand-written examples ("give me
  five minutes" → `felt_presence`, …) move into the tool descriptions.
- There's no privacy check on local turns: nothing leaves the LAN.
- **The privacy check stays wherever data would leave:** skill phrasing
  that still uses the cloud, `web_search`/`delegate_research` queries,
  and the cloud fallback. It runs on the same 12B as a one-off call and
  pays the ~2 s cache swap. That's rare, so acceptable.

**Skills need real parameter schemas.**
- Each skill's manifest gets a JSON-schema `parameters` object, so the
  model fills them properly. Today they're free-text hints in the router
  prompt.
- `parse_router_response`'s repair logic is no longer needed for tool
  calls (the server parses them).

**Screen reactions:**
- Local-first on the same model: the image plus her screen instruction,
  with `json_schema` output.
- Cloud Gemma 26B is only the fallback.

**The diary writer** moves local too, which is what makes a *private*
diary possible (it can read everything).

**Cloud leftovers:**
- `web_search`/`delegate_research`, which are external by nature
- a fallback when felt-llm is unhealthy
- the persona eval's reference arm

**Remaining phases, in order:**
1. **A: the `felt-llm` stack** as above, with the 12B preset.
2. **C': the felt-core port.**
   - `local_llm.py` (OpenAI client, tools, `json_schema`)
   - skill parameter schemas
   - the chat orchestrator moves to a single call with tools; router and
     privacy are removed from local turns
   - the warm-up loop keeps the persona prefix hot
   - metrics with `cache_n`
3. **D': switch-over.**
   - A feature flag `local_first=true` flips chat, screen reactions and
     the diary together; the rollback is flipping it back.
   - Measure 30+ real turns.
4. **F: desktop cleanup and Ollama removal**, as before.

**Blocked on 2026-09-29:** the server's 500 GB backup HDD disappeared
after the P104 install (all six SATA links down, `SStatus 0`, still gone
after a reseat and a SCSI rescan). With no local full backup, the deploy
gate aborts every update, so nothing new deploys until it's back. That
includes felt-core `ad0c221` and the felt-llm stack.

---

## Why

### 1. Ollama is fragile here, and it is down right now

- **Nitro5:** `ollama.service` has been `failed` since boot at
  2026-09-26 10:20:54. Its models live on NFS
  (`OLLAMA_MODELS=/mnt/clockmost-models/ollama`, i.e.
  `192.168.1.110:/home/ai-models` via `x-systemd.automount`,
  `idle-timeout=600`). The automount hit `start-limit-hit` at boot, and
  Ollama died with `mkdir /mnt/clockmost-models/ollama: no such device`.
  So felt-core's router, privacy check and local chat are all failing
  today. Privacy fails closed, which is safe, but the local reply fails as
  well.
- **Desktop:** Ollama already died mid-session twice (2026-09-21). That's
  why felt-animation has a health loop that restarts the `OllamaServe`
  scheduled task.
- Ollama 0.34 is itself a wrapper around llama.cpp's `llama-server`. The
  journal shows `using llama-server for model` and
  `/usr/lib/ollama/llama-server --model …`. Removing Ollama removes a layer.
  It doesn't change the inference engine.

### 2. The router-latency root cause is cold starts, not CPU speed

The audit's "router p50 **31.9 s**" came from a handful of samples that
were mostly cold. Today's `/v1/metrics/latency` shows the same shape:
router n=4, p50 1.5 s, **max 32.7 s**; privacy n=4, p50 0.5 s, **max
13.0 s**. The Ollama journal (boot -1, 2026-09-25 22:15) breaks down the
32.65 s call:

| Step | Time | Evidence |
|---|---|---|
| Load `qwen2.5:1.5b` for CPU **over NFS**. Ollama disables mmap for CPU loads, so the whole 0.94 GB file is read over the network. | 9.8 s | `llama-server started in 9.79 seconds`, `disabling mmap … reason=cpu` |
| Wait for the privacy call. It runs concurrently (`brain.py` `privacy_task`), but Ollama has 1 slot (`OLLAMA_NUM_PARALLEL:1`), so the two requests are serialised. | 3.0 s | privacy prompt: 725 tokens at 242 tok/s |
| **Router prompt evaluated from scratch on CPU**: 3,783 tokens at ~202 tok/s | **18.7 s** | `prompt eval time = 18748.38 ms / 3783 tokens` |
| Decode ~25 tokens at ~26 tok/s | 0.9 s | `eval time = 927.95 ms / 25 tokens` |
| **Total** | **32.65 s** | `[GIN] … 32.653021148s … POST "/api/chat"` |

The **same router call when warm** takes **1.51 s**. The prompt cache
restored 3,763 of 3,791 tokens, so only 28 new tokens were evaluated
(0.30 s) and 19 tokens decoded (0.69 s). A warm privacy call takes
0.47–0.67 s. The chat model's cold GPU load over NFS took 18.3 s.

Why the calls are so often cold:

- `OLLAMA_KEEP_ALIVE=30m` expires between sessions.
- The Nitro5 reboots most days (boots on 09-24 21:10, 09-25 21:32,
  09-26 10:20).
- `MAX_LOADED_MODELS=2` also has to hold Orpheus and the bench models.
- Each reload goes through NFS.
- `router.py` puts **today's date in the first sentence** of the 3.8K-token
  system prompt. The cached prefix is therefore invalid from midnight on,
  and the first call of each day re-evaluates everything.

CPU contention is **not** the cause. Prompt eval ran at a steady
200–240 tok/s, and the load average was 0.06 at idle. Only one voice-turn
stage uses the CPU at a time: STT, then router/privacy, then reply, then
TTS.

**Headroom risk:** the router prompt is 3,783–3,813 tokens, and Ollama gave
it `n_ctx` 4096. That's 93 % full. A few more skills or examples and
Ollama silently truncates the prompt.

### 3. llama.cpp does the model management natively (verified 2026-09-26)

Source: `tools/server/README.md` and `server-models.cpp` on master.
**Required version: ≥ v0.5.0 = build `b11146` (2026-09-23).** It includes
the router eviction-race fix (#29217, 2026-09-22), the LRU scheduler
(#26572, 2026-08-07) and the model-management API (#23976). The CachyOS
repo's `llama-cpp 0.4.0` predates these fixes, so don't use it.
Prebuilt Linux CUDA tarballs are on the releases page:
`llama-b<N>-bin-ubuntu-cuda-13.4-x64.tar.gz`, plus
`cudart-llama-b<N>-bin-ubuntu-cuda-13.4-x64.tar.gz`. The Nitro5 driver
reports CUDA 13.4.

Router mode means `llama-server` started **without** `-m`. Each model runs
as its own child process, and requests are routed by the `"model"` field.

| Need | Native feature |
|---|---|
| Max number of loaded models | `--models-max N` (default 4, 0 = unlimited). When full, the **idle LRU** model is evicted. A busy model is never evicted. |
| On-demand load | `--models-autoload` (default on), or `?autoload=false` per request |
| Explicit load/unload | `POST /models/load` / `POST /models/unload` `{"model": …}`, `GET /models` (status: `loaded`, `loading`, `sleeping`, `unloaded` + `failed`/`exit_code`), `GET /models/sse` |
| Idle unload (Ollama's `keep_alive`) | `--sleep-idle-seconds N`. This is a normal server arg, so it can be set **per model in the preset**. It frees weights and KV. The child process stays alive and wakes on the next request. `/health`, `/props`, `/models` and `/metrics` don't count as activity. |
| Per-model options | `--models-preset file.ini`: one section per model, and keys are CLI flags without dashes (`c`, `ngl`, `dev`, `t`, `np`, `cache-ram`, …). A `[*]` section holds shared defaults. Preset-only keys: `load-on-startup`, `stop-timeout`. |
| CPU-only instance | `ngl = 0` plus `dev = none` in that model's section |
| JSON output | `/v1/chat/completions` with `response_format: {"type":"json_schema","schema":…}` (grammar-constrained), or `json_schema`/`grammar` on `/completion` |
| Multimodal | `--mmproj` / an mmproj file next to the model in `--models-dir`. mtmd supports Moondream2, SmolVLM, Qwen2.5-VL, Gemma 3. |
| Endpoints | OpenAI: `/v1/chat/completions`, `/v1/completions`, `/v1/models`. Native: `/completion` (raw prompt), `/health`, `/props`, `/slots`, `/metrics` (`--metrics`) |
| Auth | `--api-key-file` (router only; children don't get it) |

**The gaps native mode leaves, and how this WP covers each one:**

1. **Eviction is count-based LRU.** It isn't VRAM-aware, and nothing can be
   pinned as "never evict". Fix: `--models-max 2` with exactly two resident
   presets (router on CPU, chat on GPU). Orpheus (offline, WP-19) is
   handled by `orpheus_gen.py`, which explicitly unloads chat, loads
   Orpheus, and then reverses both.
2. **There is no Ollama API** (`/api/chat`, `/api/generate`, `/api/tags`,
   `/api/ps`). Every caller is ported to `/v1/chat/completions` or
   `/completion`. That's the code half of this WP.
3. **There is no per-request `keep_alive`.** Use per-preset
   `sleep-idle-seconds` instead. Router and chat don't set it, so they stay
   resident.
4. **The router's CLI args override the preset.** Put per-model flags only
   in the INI. The CLI gets only host, port, preset, models-max, no-ui,
   api-key-file and metrics.
5. **Defaults to override:** `-ngl` defaults to `auto` and `--fit` to `on`.
   `--cache-ram` defaults to **8192 MiB** per child, on a 15 GiB box, and
   `-np` defaults to auto. Set all of these explicitly.
6. **Nothing re-warms the prompt cache after a restart.** A warm-up loop in
   felt-core does it (Do, step 3).
7. **Process supervision** is systemd's job: `Restart=on-failure`.

**llama-swap** is MIT-licensed, has ~5.8k stars, and is very active (v259,
2026-09-26). It offers TTL, groups and swap policies, but those only add a
second proxy and a Go binary on top of features the router now has. A
**custom Python supervisor** would re-implement the router. Both are
**rejected**. "Doing the management ourselves" means owning the preset INI,
the systemd unit, the model manifest and the warm-up, all in git.

### 4. The desktop doesn't need a local LLM

- **felt-animation's reaction picker** (`reaction.py`) asks `qwen2.5:1.5b`
  on the desktop GPU to pick one tag from ~110 scanned tag folders.
  - It runs for **every reply without a valid server tag**: plain chat,
    every screen reaction and every event line. felt-core only sends
    `X-Animation-Tag` for skills.
  - `X-Emotion` (screen/event lines) is only partly redundant with it. The
    reaction table's `reply:<emotion>` replaces the classifier's tag only
    when that tag is the fallback or `idle`.
  - It sits on the reply's critical path:
    `asyncio.gather(generate_cues, _resolve_reaction_tag)` finishes before
    playback starts.
  - The log shows 6 "unknown tag" answers (`show_off`,
    `emotion/sleepy_yawn`, …) that fell back to `gesture/talking`.
  - **Verdict: move it to the Nitro5's CPU router model over the LAN.** Use
    a JSON-schema `enum` of the known tags, so an invalid tag is
    impossible. Set a 2.5 s timeout, with the existing fallback tag.
  - When the Nitro5 is off there's no voice anyway: felt-core's TTS lives
    there too. So the LAN dependency loses nothing.
- **felt-vision** (`llava` on the desktop's Ollama) has been reachable only
  as felt-tray's fallback when `/v1/react/screen` returns 503
  `cloud_unavailable` (WP-07).
  - `%TEMP%\felt-vision.log` shows 44 calls, the last on
    **2026-09-22 23:00**, all before WP-07.
  - `felt-tray.log` has 0 "cloud unavailable" lines since 09-22.
  - It is effectively dead code on a model that needs ~4.7 GB. What
    replaces it is **Mario's decision** (below).
- **A signed alternative on Windows isn't worth it.** Smart App Control
  blocks the unsigned `E:\Felt\tools\llamacpp\llama-server.exe`. The only
  signed options are Ollama itself or LM Studio, which is just another
  wrapper.
- **Privacy line:** the reply text and window titles go only to the Nitro5
  (LAN, local). Nothing here adds a cloud path. The existing privacy
  classifier still gates any cloud use, exactly as today.

## Inventory: every Ollama call site (2026-09-26)

There are 10 HTTP call sites in 6 files. felt-core's two helpers fan out to
10 callers. felt-dashboard and felt-voice make **0** runtime calls
(felt-voice only mentions Ollama in comments). `~/felt-voice-next/bench_*.py`
on the Nitro5 are offline benchmarks from the voice A/B. They are historical
and not ported.

| # | Where | Endpoint | Model | Options | Called | Budget / timeout |
|---|---|---|---|---|---|---|
| 1 | felt-core `router.py` `decide_tool` | `/api/chat` | `router_model` `qwen2.5:1.5b` | `temperature 0`, `num_gpu 0`, no `num_ctx` (Ollama gave 4096, prompt 3.8K tokens), no JSON mode, `stream false` | every chat turn not caught by the presence fast path | target ≤ 2 s; timeout 60 s |
| 2 | felt-core `privacy.py` `is_safe_for_cloud` | `/api/chat` | `router_model` | `temperature 0`, `num_gpu 0`, one-word answer, fails closed | chat turn (concurrent with #1), tool output (`brain.py` 463), history window (479), screen description (902), events (`events.py` 326) | target ≤ 1 s; **timeout 15 s** (the cold 13 s nearly hit it) |
| 3 | felt-core `brain.py` `_ollama_chat` via `_local_reply` | `/api/chat` | `ollama_model` `qwen2.5:3b` (GPU) | `num_ctx 4096`, `num_predict 160`, no JSON | email summary (254), chat local route (387), skill phrasing local (506), screen-context local (893), event local (`events.py` 345) | timeout 120 s |
| 4 | felt-animation `reaction.py` `classify_reaction` | `/api/generate` (desktop) | `qwen2.5:1.5b` | none; plain-text tag, validated after | every reply without a valid server tag | on the reply's critical path; timeout 15 s |
| 5 | felt-animation `ollama_health.py` | `GET /api/tags` every 60 s | none | restarts the `OllamaServe` task | continuous | 3 s |
| 6 | felt-vision `main.py` `/analyze` | `/api/generate` (desktop) | `VISION_MODEL` = `llava` | `images: [b64]` | only via felt-tray `watcher._felt_vision_fallback` on a 503 | 30 s (tray: 15 s) |
| 7 | `LaunchFelt.ps1` lines 1–21 | `GET /api/tags` | none | starts `OllamaServe` | each launch | 2 s |
| 8–10 | `tools/sounds/nitro/orpheus_gen.py` | `/api/generate` raw (non-stream and stream), `GET /api/ps` | `hf.co/unsloth/orpheus-3b-0.1-ft-GGUF:Q4_K_M` | `raw`, `keep_alive 10m`, `num_ctx 2048`, `seed`, `stop`, `num_predict` | offline WP-19 batches | none |

**Config keys:**

- felt-core `config.py`: `ollama_url`, `ollama_model`, `ollama_num_ctx`,
  `router_model`. `.env.example`: `FELT_OLLAMA_URL/MODEL/NUM_CTX`,
  `FELT_ROUTER_MODEL`.
- **Server** `/home/clockmost-infra/projects/felt-core/.env` is
  **gitignored and hand-edited**:
  `FELT_OLLAMA_URL=http://192.168.1.104:11434`, `FELT_OLLAMA_MODEL`,
  `FELT_ROUTER_MODEL`.
- felt-animation: `FELT_ANIMATION_OLLAMA_URL/MODEL` (`.env` +
  `.env.example`).
- felt-vision: `OLLAMA_URL`, `VISION_MODEL`.
- felt-tray: `FELT_VISION_URL`.
- felt-core tests that mention Ollama: `test_ollama_chat_options.py`,
  `test_local_paths_audit.py`, `test_brain_*`, `test_react_event.py`,
  `test_metrics.py`, `test_ui_action_plumbing.py` (48 lines).

**Models held today:**

- Nitro5, via NFS; each blob file is named after its own SHA-256:
  - `qwen2.5:1.5b`: `sha256-183715c4…18a5b4`, 986,048,512 B, Q4_K_M
  - `qwen2.5:3b`: `sha256-5ee4f07c…31caa6`, 1,929,903,008 B
  - Orpheus: `sha256-4e94a925…9f7ab9`, 2,092,569,120 B
  - plus unused `qwen2.5:7b`, `llama3.1:8b`, `mistral:7b`, `llama3.2:3b`,
    `qwen3:4b` and `gemma3:4b`
- Desktop: `qwen2.5:1.5b`, `llava` (4.7 GB) and `moondream` (1.7 GB).

## ⚠ Mario's first decision: the screen fallback when the cloud is down

Retiring the desktop Ollama removes the only local *image* model. The
choice is what she does when `/v1/react/screen` answers 503
(`cloud_unavailable`, e.g. Gemma's cap or an outage):

1. **Title-only local line (recommended).**
   - felt-tray's fallback sends `"Mario is in <app>: <window title>"` to the
     existing `/v1/context/screen`. felt-core's `process_screen_context`
     then applies its privacy check and the local chat model on the
     Nitro5.
   - She still speaks (the "never quiet" rule holds), but she can't see
     pixels.
   - No new model, no VRAM or RAM cost, and felt-vision is deleted.
   - In 4 days this path fired 0 times.
2. **A local VLM on the Nitro5 CPU.** Moondream2 (mtmd-supported, ~1.9 GB)
   as a third preset, with `sleep-idle-seconds 300`.
   - Real image understanding offline, but it's slow on CPU (expect several
     seconds per image, to be measured) and needs ~2–3 GB more RAM.
   - It also needs `--models-max 3`, which re-opens the eviction question.
3. **Keep the desktop's Ollama just for llava.** This contradicts the goal
   of this WP.

Until Mario answers, the implementer does everything else and leaves
felt-vision in place, unused.

---

## Do

### 0. Nitro5 install (`E:\Felt\tools\felt-llm\`, committed in the umbrella)

**Files:**

- `manifest.toml`: the pinned build (`b<N>` ≥ `b11146`) with both tarball
  URLs and their SHA-256, plus each model's name, source (Ollama blob
  digest), size and target path. Reuse it in WP-34.
- `felt-models.ini`, the preset:
  ```ini
  version = 1
  [*]
  jinja = true
  fit = off
  cache-ram = 512

  [router-1.5b]          ; router + privacy + reaction picker, CPU only
  model = /home/benylin/felt-llm/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
  dev = none
  ngl = 0
  c = 18432              ; np 3 -> 6144 tokens per slot (router prompt is 3.8K)
  np = 3
  t = 8
  tb = 8
  load-on-startup = true

  [chat-3b]              ; local chat, GPU
  model = /home/benylin/felt-llm/models/qwen2.5-3b-instruct-q4_k_m.gguf
  ngl = all
  c = 4096
  np = 1
  load-on-startup = true ; false until the chat caller flips (step 6)

  [orpheus-3b]           ; offline WP-19 only
  model = /home/benylin/felt-llm/models/orpheus-3b-0.1-ft-q4_k_m.gguf
  ngl = all
  c = 2048
  np = 1
  load-on-startup = false
  sleep-idle-seconds = 600
  ```
- **Sampling parity:** before removing Ollama, read the effective defaults
  (`ollama show --parameters` / `--modelfile` for both qwen models; the
  qwen manifests have no params layer, so Ollama's built-ins apply). Set
  the same `temp`, `top-k`, `top-p`, `repeat-penalty` and `min-p` in
  `[chat-3b]`. llama-server's defaults differ (e.g. `min-p 0.05`,
  `repeat-penalty 1.0`).
- `felt-llm.service`, a system unit like `felt-voice.service`:
  - `User=benylin`, `After=network-online.target`, `Restart=on-failure`
  - `ExecStart=/opt/felt-llm/current/llama-server --host 0.0.0.0 --port 8080 --models-preset /home/benylin/felt-llm/felt-models.ini --models-max 2 --no-ui --metrics --api-key-file /home/benylin/felt-llm/api-keys`
  - Port 8080 is free on the Nitro5. It has 22, 8188, 8421 and 10050.
- `install.sh`, idempotent:
  - Download both tarballs, verify their SHA-256, and extract them to
    `/opt/felt-llm/llama-b<N>/`. Point the `current` symlink at that
    directory; rolling back means repointing the symlink.
  - Copy the three blobs from the server
    (`scp clockmost-claude:/home/ai-models/ollama/blobs/sha256-<digest>`,
    or from the NFS mount while it's up) to
    `~/felt-llm/models/<name>.gguf`, on **local disk** (126 GB free).
  - Verify that `sha256sum` equals the digest. Reusing the blobs gives
    byte-identical weights, so behaviour matches and nothing needs
    downloading. Don't re-download from Hugging Face: the official
    `Qwen/*-GGUF` files are different conversions.
  - If the prebuilt tarball doesn't run on CachyOS, build from the same tag
    with the installed CUDA 13.3.1 (`cmake -DGGML_CUDA=ON`). Record that in
    the notes.
- **Needs Mario:** `sudo` on the Nitro5 asks for a password. Installing to
  `/opt` and the system unit are his steps. Hand him the exact commands.
- **API key:**
  - Generate one into `~/felt-llm/api-keys` (mode 600).
  - Put the same key in felt-core's sops `secrets.env` as
    `FELT_LLAMACPP_API_KEY`, and in felt-animation's `.env`.
  - Never commit or print it.
- **Verify:**
  - `GET :8080/models` shows `router-1.5b` loaded.
  - The log shows `n_ctx_slot = 6144` and no CUDA device for the router.
  - `nvidia-smi` shows no new process for the router.

### 1. felt-core: one local-LLM client with a per-caller backend flag

- New `src/felt_core/local_llm.py`:
  `chat(messages, *, purpose, model, max_tokens=None, temperature=None, json_schema=None) -> LocalReply(text, prompt_n, cache_n)`.
  - It speaks either Ollama `/api/chat` (the current payloads, unchanged)
    or llama.cpp `/v1/chat/completions` with `model`, `max_tokens`,
    `temperature` and `response_format`, plus a `Bearer` key.
  - From llama.cpp it reads `usage` and `timings` (`prompt_n`, `cache_n`).
- Config (`config.py` + `.env.example`), all non-secret:
  ```
  llamacpp_url: str = "http://localhost:8080"
  llamacpp_router_model: str = "router-1.5b"
  llamacpp_chat_model: str = "chat-3b"
  llm_backend_router: str = "ollama"    # "ollama" | "llamacpp"
  llm_backend_privacy: str = "ollama"
  llm_backend_chat: str = "ollama"
  ```
  The key comes from secrets (`llamacpp_api_key`). The server `.env` gets
  `FELT_LLAMACPP_URL=http://192.168.1.104:8080`.
- Port callers #1–#3 to `local_llm.chat`. Behaviour stays identical on
  `ollama`.
- **Router (#1):**
  - `response_format` `json_schema`:
    `{"type":"object","properties":{"skill":{"enum":[<registry names>…, null]},"params":{"type":"object"}},"required":["skill"]}`.
  - Keep `parse_router_response` as the defensive parser.
  - `max_tokens 96`.
  - **Move the date line to the end** of the system prompt, so the ~3.7K
    token prefix is identical every day. Update the router tests that
    pin the prompt text.
- **Privacy (#2):**
  - `max_tokens 3`. No grammar: the prompt already demands one word, and
    parsing still fails closed.
  - Raise the timeout to 20 s only if a *warm* p95 needs it (it shouldn't).
- **Chat (#3):** `max_tokens 160` (same `_REPLY_MAX_TOKENS`). There's no
  per-request `num_ctx`: the context now lives in the preset.
- **Metrics:** tag `router`, `privacy` and `reply(route=local)` with
  `backend=` and `cache_n=`. A warm router call should show
  `cache_n ≥ 3,600`.

### 2. felt-core: warm-up and health (replaces keep-alive tricks)

- `local_llm_watch_loop`, started in the lifespan next to the other loops:
  - Every 30 s it calls `GET {llamacpp_url}/models` (this doesn't reset idle
    timers).
  - When `router-1.5b` becomes `loaded` (first sight, a restart, a status
    change), and once after local midnight, it sends one router call and
    one privacy call with a dummy message. That fills slots 0 and 1 with
    the real prefixes.
  - It logs `local llm warm: router cache_n=… in …ms`, and **never records
    these calls in latency metrics**.
- It is a no-op while `llm_backend_router/privacy` are `ollama`.

### 3. Side-by-side switch (Ollama stays installed as the rollback)

1. Mario restarts Ollama (NFS automount) so the rollback path works. Or
   accept that today's state already has it down.
2. Deploy felt-core with every flag on `ollama`. Tests stay green.
3. Flip `llm_backend_router=llamacpp` and `llm_backend_privacy=llamacpp` in
   the server `.env`, then redeploy. These run on the CPU, so there's no
   VRAM clash with Ollama.
4. Measure 30+ real turns. **Rollback:** set the flags back to `ollama`
   and redeploy.
5. Before flipping chat, make sure Ollama holds no GPU model
   (`GET :11434/api/ps` is empty, or wait out keep-alive). Then set
   `load-on-startup = true` for `[chat-3b]`, restart `felt-llm`, and flip
   `llm_backend_chat=llamacpp`.
   - Two copies of the 3B plus the voice stack would need ~7.5 GB. **Never
     let both be resident.**
   - **Rollback:** `POST /models/unload {"model":"chat-3b"}`, then set the
     flag back.

### 4. Desktop: felt-animation reaction picker → Nitro5

- `reaction.py`: `POST {reaction_llm_url}/v1/chat/completions`, model
  `router-1.5b`.
  - Keep the prompt order: the static tag list first, the reply text last.
    That makes the ~600-token prefix cacheable in slot 2.
  - `response_format` `json_schema` `{"enum": sorted(known_tags)}`, then
    parse the JSON string.
  - `max_tokens 24`, timeout **2.5 s**, same fallback tag.
- Config: replace `FELT_ANIMATION_OLLAMA_URL/MODEL` with
  `FELT_ANIMATION_REACTION_LLM_URL=http://192.168.1.104:8080`,
  `FELT_ANIMATION_REACTION_LLM_MODEL=router-1.5b` and
  `FELT_ANIMATION_REACTION_LLM_API_KEY`. Update `config.py`,
  `.env.example` and the README.
  - Keep `FELT_ANIMATION_REACTION_BACKEND=ollama|llamacpp` until step 7,
    then remove it.
- Add `reaction pick: tag=… in …ms` at INFO. Today success isn't logged at
  all.
- Delete `ollama_health.py` and its task in `server.py`, and remove lines
  1–21 of `LaunchFelt.ps1`.
- Tests: the enum schema is built from `known_tags`; the timeout leads to
  the fallback; a non-enum answer (impossible, but still covered) leads to
  the fallback.

### 5. Screen fallback (per Mario's decision)

- If option 1:
  - Replace felt-tray `watcher._felt_vision_fallback` with
    `_title_fallback`, which calls `send_screen_context(f"Mario is in {app}: {title}", tone=tone)`.
    The screen blocklist has already run by then.
  - Remove `FELT_VISION_URL`, felt-vision's entry in `LaunchFelt.ps1`, and
    the `felt-vision` process exclusions that no longer matter (keep the
    exe-name exclusions, which are harmless).
  - Archive the felt-vision repo, noting the README.
- If option 2: add `[vision]` to the preset with an mmproj, and port
  felt-vision's `/analyze` to `/v1/chat/completions` with an `image_url`
  data URI, pointed at the Nitro5.

### 6. WP-19 tool: `orpheus_gen.py`

- `/api/generate` raw becomes `POST /completion` with `prompt`,
  `n_predict`, `seed`, `stop` and `stream`.
- `/api/ps` becomes `GET /models`.
- Wrap the batch:
  1. `POST /models/unload chat-3b`
  2. `POST /models/load orpheus-3b`
  3. run the batch
  4. `POST /models/unload orpheus-3b`
  5. `POST /models/load chat-3b`

  Put step 5 in a `finally`. Document the new procedure in the script's
  docstring.

### 7. Remove Ollama (after 3 days' soak, with Mario's go)

- **Nitro5 (Mario's sudo):**
  - `systemctl disable --now ollama`
  - remove `/etc/systemd/system/ollama.service.d/override.conf`
  - `pacman -Rns ollama ollama-cuda`
- **Server:** leave `/home/ai-models/ollama` in place. First list its other
  consumers (`grep -r ai-models` in clockmost-infra) and put the result in
  the notes. Deleting it is a separate call for Mario.
- **Desktop:**
  - `Unregister-ScheduledTask OllamaServe` (check the ClaudeElevated
    allowlist; otherwise it's Mario's step)
  - `winget uninstall Ollama.Ollama`
  - after Mario says OK, delete `%USERPROFILE%\.ollama` (~7.5 GB)
  - delete the unused unsigned `E:\Felt\tools\llamacpp\`
- **Code:**
  - Remove the `ollama` branches and the `llm_backend_*` flags, and rename
    `ollama_*` config to `local_llm_*`, keeping the old env names as
    deprecated aliases for one release.
  - Update `00-implementer-context.md` (machines table, the Nitro5 rule
    "swapping Ollama") and WP-34's Nitro5 "Ollama" bullet.
  - `grep -rniE "11434|ollama"` over the repos must hit only history and
    docs.

## Resource plan (Nitro5, measured and computed)

**VRAM (6,144 MiB):**

| Item | MiB | Source |
|---|---|---|
| felt-voice (Chatterbox-Turbo + RVC, resident) | 2,460 | `nvidia-smi` today |
| ComfyUI `--lowvram` idle | 110 | `nvidia-smi` today |
| chat-3b: weights 1,841 + KV 4096 × 36 KiB = 144 + compute ~300 + CUDA context ~250 | ~2,535 | GGUF size; 36 layers × 2 KV heads × 128 × f16 |
| **Total resident** | **~5,100** | matches the measured 5.2 GB peak during synthesis |
| *If the router were on GPU:* weights 940 + KV 6144 × 28 KiB = 168 + compute ~150 + its own CUDA context ~250 | +~1,500 | **6.6 GB, doesn't fit**, so the router stays on CPU |

**RAM (15.3 GiB total, 7.5 GiB available today):**

- felt-voice RSS is 5.6 GB and ComfyUI 1.7 GB.
- router-1.5b:
  - weights 0.94 GB, mmapped from local disk
  - KV 18,432 × 28 KiB = 504 MiB
  - compute ~70 MiB
  - prompt cache capped at 512 MiB (default 8 GiB!)
  - **≤ 2.1 GiB** in all
- The chat child's host side is ~0.4 GiB.
- That leaves ≥ 4.5 GiB free.

**CPU (Ryzen 7 5800H, 8C/16T, SMT pairs 0-1, 2-3, …):**

- The router uses `t 8` / `tb 8`. Its three slots decode together through
  continuous batching.
- **No pinning in the base plan**, since the evidence shows no contention.
- Knob: if an A/B with TTS running at the same time slows router decode by
  > 20 %, add `cpu-range` to the preset and record the result.

**Expected latency:**

| Call | Warm | After a Nitro5 boot |
|---|---|---|
| router | ≈ 0.2 s prompt (≤ 60 new tokens at 200 tok/s) + ≤ 25 tokens at ~26 tok/s ≈ **1.0–1.5 s** | the warm-up absorbs the one-off 3.8K-token evaluation (~19 s) and the load (~1 s from local disk instead of 9.8 s over NFS) |
| privacy | **≤ 0.7 s** | same |

Router and privacy no longer queue behind each other, because each has its
own slot.

## Accept

1. On the Nitro5:
   - `GET :8080/models` shows `router-1.5b` and `chat-3b` loaded, and
     `felt-llm.service` is enabled.
   - After a **cold reboot**, both come up with no NFS mount present.
   - The warm-up line is logged within 60 s of the router loading.
2. From `/v1/metrics/latency`, over ≥ 30 real turns including the first
   turn after a boot:
   - **router p50 ≤ 2 s, p95 ≤ 4 s**
   - **privacy p50 ≤ 1 s**, with no 15 s timeouts
   - router `cache_n ≥ 3,600` on non-warm-up calls
3. Routing parity:
   - Replay 50 recent real user messages against both backends side by
     side (on the LAN, before Ollama is removed). ≥ 48 give the same
     skill, and every difference is written up.
   - The router always returns valid JSON (schema).
4. VRAM and RAM:
   - `nvidia-smi` peak during a voice turn with synthesis stays
     **≤ 5.4 GiB**.
   - `free -m` "available" stays ≥ 3 GiB during a turn.
5. Desktop:
   - The reaction picker logs `reaction pick: tag=… in …ms` with p95 ≤ 1.5 s
     and **0 unknown tags**.
   - Nothing listens on `127.0.0.1:11434`.
   - `LaunchFelt.ps1` starts without Ollama.
6. The WP-19 Orpheus script regenerates one known take through
   `/completion`, and chat-3b is reloaded afterwards.
7. felt-core, felt-animation and felt-tray tests are green. After step 7,
   the `ollama|11434` grep is clean and no Ollama process or package is
   left on either machine.
8. Rollback is proven once: flip router/privacy back to `ollama`, take one
   turn, then flip forward again (before step 7).

## Notes

- **Live issue found while planning:** the Nitro5's Ollama has been down
  since 10:20 today (NFS automount `start-limit-hit`), so felt-core's local
  paths are failing now. Step 0 (models on local disk) removes this class
  of failure.
- The privacy classifier's 15 s timeout is uncomfortably close to a cold
  call (13.0 s measured). After this WP, cold calls are handled by the
  warm-up rather than by the timeout.

## Additions from the llama-canvas spike (2026-09-26)

Source: `F:\workspace\needs-to-spike-llama-canvas-vault\SPIKE-FINDINGS.md`,
a llama.cpp-first knowledge vault. It independently arrived at this same
design: router mode, `--models-max`, presets, and dropping Ollama. Fold
these in when WP-36 runs:

1. **Speculative decoding with no draft model:** `spec-type=ngram-mod` on
   the `chat-3b` preset. A free generation speed-up; measure it against
   the baseline before keeping it. (S, low risk.)
2. **Don't set flags that are already defaults** (`jinja`, `flash-attn`,
   …) in the preset. Check each one against the pinned build's defaults
   and keep only what changes behaviour. (S, cleanliness.)
3. **Self-compile llama.cpp for the Nitro5** (hardware-tuned CUDA build)
   as a deliberate step *after* the prebuilt setup is stable and measured.
   The vault reports 10–44% gains; prove it with before/after tokens/s.
   (M.)

Documented but not needed now:
- KV-cache quantisation (`cache-type-k/v=q8_0`) as a later RAM/VRAM lever;
- explicit batch/ubatch tuning, since no CPU contention has been measured.
