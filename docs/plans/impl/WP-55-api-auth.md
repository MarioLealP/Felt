# WP-55: felt-core API auth + TLS

**Why** (found 2026-10-01 in the clockmost security review,
`F:\workspace\runbooks\clockmost-security-visibility-plan.md`, item I): felt-core
on `:8420` has **no authentication**, and is served over plain HTTP. From any LAN
host, `GET /v1/history` returned 200, so anyone who could reach it could read or
delete conversation history, the diary and self-memories, and push screen or
context events. Voice audio and screen context also cross the LAN unencrypted.

**Stopgap in place:** a `DOCKER-USER` drop on the server
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
