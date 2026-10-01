# WP-55: felt-core API auth + TLS

**Why** (found 2026-10-01 in the clockmost security review,
`F:\workspace\runbooks\clockmost-security-visibility-plan.md`, item I): felt-core
on `:8420` has **no authentication**, and is served over plain HTTP. From any LAN
host, `GET /v1/history` returned 200, so anyone who could reach it could read or
delete conversation history, the diary and self-memories, and push screen or
context events. Voice audio and screen context also cross the LAN unencrypted.

**Stopgap (retired 2026-10-01, see Progress):** a `DOCKER-USER` drop on the server
(`ops/sbin/lan-port-scope.sh` in clockmost-infra) lets only the desktop (`.74`)
and the laptop (`.104`) reach 8420 from the LAN. It does **not** cover malware
on the desktop itself. (Other containers can no longer reach her: since
2026-10-01 only felt-llm and drive-rag share her Docker network, `felt`.) Hence this WP.

## Scope
1. **Token auth** in felt-core: one shared bearer token (sops `secrets.env` on
   the server, client config on desktop and laptop), required on every route
   except the healthcheck. Constant-time compare. Reject with 401.
2. **Clients go through Caddy over HTTPS**: `https://felt.clockmost.com` (the
   wildcard cert is already in place), not `http://192.168.10.110:8420`. That
   applies to felt-desktop-agent, the dashboard, the laptop voice client, and the
   proactive and audio fetches.
3. **Close the published port**: drop `8420:8420` from compose and the `8420`
   entry in `lan-port-scope.sh` once every client is moved.

## Not in scope
- mTLS / per-device client certificates. Over TLS, a token gives most of the
  benefit for little effort; revisit only if per-device revocation is wanted.

## Done when
- An unauthenticated request to any data route returns 401.
- Every client works over `https://felt.clockmost.com`.
- `:8420` is no longer published on the host.

## Progress
- 2026-10-01: token check is in felt-core (`FELT_API_TOKEN`; it does nothing
  while unset). The exemptions are only the OpenAPI/docs pages (the healthcheck
  probes `/openapi.json`) and CORS preflights. The websocket accepts the
  header or `?token=`. The clients (tray, felt-animation, dashboard) send
  `FELT_CORE_TOKEN` / `VITE_FELT_CORE_TOKEN` when it's set.
- 2026-10-01: `https://felt.clockmost.com` is live (Caddy → `felt-core:8420`
  over `front-felt`; infra `20b96c6`, `73083f8`, `0efeec2`). No SSO and no
  tunnel entry. It resolves on the LAN via the pihole wildcard.
- 2026-10-01: Mario generated the token into the three client `.env` files
  (the agent's permission system blocks secret-store writes). The tray,
  felt-animation and the dashboard (rebuilt) now use `https://felt.clockmost.com`.
  Verified: zero direct `:8420` requests, all traffic arrives via Caddy.
- 2026-10-01: `:8420` unpublished (infra `17ee255`). Removed its
  `lan-port-scope.sh` entry (installed and rerun) and the stale firewalld
  `.74 → 8420` rich rule.
- 2026-10-01: `/shopping-list` phone page (Mario: "SSO whenever possible";
  "still VPN only"). Caddy `@felt_sso` puts forward-auth on `/shopping-list`
  and `/v1/shopping-list*` (Authentik app `felt`, Admins), infra `363b306`.
  felt-core skips its token check for exactly those method+path pairs only
  (`_SSO_GATED`, `127e8c2`). Safe because Caddy is the only way in.
- 2026-10-01: **enforced.** Mario ran the `FELT_API_TOKEN` sops set via
  `bin/secrets` (infra `3276c38`). Verified: no token → `/v1/history` 401,
  `/openapi.json` 200 (healthcheck), `/shopping-list` → 302 SSO, and 11/11
  client requests authorized over 70 s with 0 rejected. The CORS preflight
  allows `authorization`. No client uses `/v1/chat/ws`.

**✅ Done 2026-10-01.** Live check left: shopping list on the phone (SSO login).
Rotating the token = regenerate it into the three client `.env` files + `bin/secrets set`
on the server (secret-store writes need Mario; the agent's permission
system blocks them), then rebuild the dashboard and restart Felt.
