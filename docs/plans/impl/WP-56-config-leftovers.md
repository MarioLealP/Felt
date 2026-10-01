# WP-56: config leftovers found in the clockmost security pass (2026-10-01)

Found while splitting the server's Docker networks (clockmost item K). Mario:
"Ignore felt problems, just throw on her WP backlog". Nothing here is urgent.
Everything already fixed is listed at the bottom.

## Open
1. ~~**`FELT_OLLAMA_URL` → `http://192.168.10.104:11434` is dead.** Nothing listens
   on the laptop's :11434 (connection refused, so it isn't the firewall).
   felt-llm on the server now does her local-LLM jobs. If nothing still reads
   this setting, drop it from felt-core config and from the sops secrets in the
   infra repo (`projects/felt-core/secrets.env`).~~ **Done 10-01** (infra
   `a383fc9`): nothing read it since WP-36. Removed `FELT_OLLAMA_URL`,
   `FELT_OLLAMA_MODEL` and the also-dead `FELT_ROUTER_MODEL` with
   `sops unset`, so the file was never decrypted to disk.
2. **drive-rag still answers through Gemini Flash via ninerouter.** That's a cloud
   call, which contradicts the "Felt is fully local" rule. felt-core itself
   dropped its Gemini/ninerouter keys (WP-36 D''). Either point drive-rag at
   felt-llm, or accept it as the one documented exception.
3. ~~**Stale comment in `projects/felt-llm/compose.yaml`:** "Rollback: docker
   compose down (felt-core falls back to the cloud)". There's no cloud fallback
   any more.~~ **Done 10-01** (`a383fc9`).
4. ~~**felt-core `30bba1ebc753`** (built 2026-10-01 06:38) never deployed, because
   CI's promote step was broken by stale Gitea secrets, since fixed. It ships
   with her next push to main (Mario: "Next push").~~ **Done 10-01**: shipped
   with `e5ddf11`, promoted by CI.

5. **Wazuh alert triage (ties into WP-43).** clockmost is getting Wazuh (security
   monitoring of the server, desktop and laptop). Level ≥12 alerts land on the
   `clockmost` ntfy topic she already follows. Proposed after its week-1 review:
   a Felt-only topic for mid-level (8–11) alerts, so she does first-line triage.
   Mario: "there is a WP for felt to also work as a first step on triage".

6. **Found 10-01: the item-K network split cut felt-core off from poe2rag and
   SearXNG.**
   - **poe2rag (her WP-29 wiki skill):** fixed in infra `768147c`. poe2rag joins
     `felt` as external, like felt-llm and drive-rag (item K's "explicit link
     where an app really needs another").
   - **SearXNG (her `web_search` skill, `http://searxng:8080`):** there is **no
     SearXNG anywhere in the infra repo** and no container, so web search was
     dead before the split too. It was probably never redeployed after the
     2026-08 rebuild. Decision for Mario: deploy one (on `felt`), or retire the
     skill.

## Already fixed (for the record)
- Her LAN URLs (voice, desktop agent, HA, ComfyUI) were still on 192.168.1.x
  after the R7000 renumber, causing 175 ConnectErrors in 6 h. Fixed in infra
  `82bb7bd`.
- She has her own Docker network: `felt`, 172.29.39.0/24, with felt-core pinned
  at **172.29.39.39**. Only felt-llm and drive-rag share it. She left `edge` and
  `authentik` (never used). Infra `7ff43b4`.
