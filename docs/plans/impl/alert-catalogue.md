# Alert catalogue — what actually arrives, and who handles it

Built 2026-10-03 from the 1,449 alerts felt-core stored from the clockmost
ntfy topic (09-11 → 10-03). Each type: how often it fires, whether a
RESOLVED follows on its own, and a **proposal** to go through with Mario,
type by type (WP-42 decisions log, 10-03: "she is the first responder";
"any cyber related stuff should be throwing at you, if its server
restarted, then she can handle it since there is nothing to handle").

**Handlers**
- **Felt** — she reads it, checks it read-only where she can (container
  status, Zabbix, "is that host just off?"), files it and/or tells Mario in
  her own words. Only types her 12B is shown to get right (tested on these
  real alerts first).
- **Claude** — security, and anything whose cause needs real digging.
  Felt hands it over; the result comes back to Systems (WP-58).
- **Mario** — needs a decision or hands-on work; Felt notifies with her take.
- **WP-41** — shouldn't be sent like this at all; fixed at the source on the
  server (thresholds, expected-event suppression, dedupe).

**Tiers** (10-02, 8.5): **urgent** = loud notification · **high** = normal
notification · **default** = in Systems, quiet · **low** = history only.
Notifications pop on every device (Mario 10-03).

## Security → Claude

| Type | Count | Self-resolves | Proposal |
|---|---|---|---|
| Wazuh file-integrity (sensitive file / autostart / SSH key changed) | 75 in 3 days | no RESOLVED exists | **Claude**, high. Almost all were our own infra changes (deploys, setup). Claude checks each change against recent infra commits and deploys: expected → filed, unexplained → urgent to Mario. |
| Honeypot touched / host banned | 3 | — | **Claude**, urgent. Who touched it, from where, banned or exempt, anything else from that host. |
| Authentik login-flow spike (possible brute force) | 2 | ~9 min | **Claude**, high. Real attack vs. Mario logging in a lot. |
| CrowdSec bouncer not enforcing | 1 | ~1 min | **Claude** if it lasts >10 min, otherwise Felt files it. |
| Trivy weekly scan (191 critical, 2,487 high fixable) | weekly | — | **Claude**, default. Weekly digest: what's actually exposed vs. noise, what to update. |
| Wazuh out-of-memory kill | 6 | — | Not security, it's resources. **Felt**, default: which host, what got killed. High if it's felt-core/llm or repeats. |

## Backups and updates → Mario, with Felt explaining

| Type | Count | Self-resolves | Proposal |
|---|---|---|---|
| Backup FAILED (full / precious) | 26 (burst 09-28/29) | no | **Mario**, urgent. Felt says it plainly ("backup failed, 3rd time tonight, restic exit 10"). Cause digging → Claude. Repeats folded into one. |
| Storage/backup check (disk not mounted, SMART, snapshots stale) | 6 | no | **Mario**, urgent. |
| Updates SKIPPED (backup failed first) | 23 | no | Folded into the backup failure it comes from; never its own notification. |
| Auto-reverting / update reverted | 14 | no | **Mario**, high. Felt names the stack and the version. |
| CI / deploy pipeline failed | 6 | no | **Mario**, high (usually Claude's own pushes, so Claude gets it too). |

## Outages that mostly fix themselves → Felt watches, Mario only if it lasts

| Type | Count | Self-resolves | Proposal |
|---|---|---|---|
| Authentik outpost disconnected | 74 | yes, ~6 min | **WP-41** (fires on deploys). **Felt**: quiet unless still down after 15 min → high to Mario (SSO is down = apps unreachable). |
| Caddy upstream unhealthy | 22 | yes, ~4 min | Same: **Felt**, high only if >10 min, naming the upstream. |
| Route check failing | 19 | yes, ~3 min | Same as Caddy. |
| Container unhealthy / stopped | 32 | yes, ~10 min | **Felt**: checks status; >15 min → high with the container and its last log lines. (twitch-robin unhealthy since 10-01, still open.) |
| Pi-hole DNS not resolving | 2 | slow (18 h once) | **Felt**, high after 10 min (DNS down hits everything). |
| Home Assistant VM not running / autostart off | 4 | ~2 min | **Felt**, high if >10 min. |

## Expected events → Felt files them, nothing to handle

| Type | Count | Proposal |
|---|---|---|
| Update deployed | 208 | **Felt**, low. Never mentioned (09-26: info → never). A line in the morning brief at most. |
| Pre-update backup ok, weekly reboot, ntfy upgraded, container version changed | ~30 | **Felt**, low. |
| Host restarted (server, desktop, Nitro5) | 30 | **Felt**, low (Mario's example). Default if the server restarted outside the Monday window. |
| Zabbix agent unavailable (desktop / laptop) | 80 | **WP-41** + **Felt**: almost always the PC is just off (resolves in ~9 h). She knows when the desktop is off, so low; default if the server's own agent is down. |

## Noise → WP-41, not sent

| Type | Count | Proposal |
|---|---|---|
| Windows service "not running" (Google Updater, AppX, Web Threat Defense) | 622 (43% of everything) | **WP-41**: these are on-demand/delayed-start services; exclude them from the Zabbix trigger. Felt never sees them. |
| Network bandwidth high on router VLAN/eth | 66 | **WP-41**: raise the threshold or sustained-only; Felt low. |
| Windows/Linux CPU, memory, swap, disk latency | ~60 | **WP-41** sustained-only; **Felt** default if it lasts. Disk space low → high. |
| Nitro5 Ollama failed / GPU overheating | 14 | **Felt**, default (the laptop node is on-demand). |
| Windows crash (unexpected shutdown / critical log) | 4 | **Felt**, high: tells Mario the PC went down hard. |
| SMART disk temperature | 2 | **Felt**, default; high if it repeats. |
| Health check WARN | 11 | **Felt**, default, saying which check. |
| Wazuh setup test | 1 | ignore. |

## Rough volume after this (last 7 days' rates)

- Notifications to Mario: about 10–20 a week, nearly all real.
- Claude: ~25 Wazuh file changes a day today, but most go away once
  Claude matches them to our own deploys (and WP-41 can tune the watched
  paths).
- Felt files everything else quietly in Systems.
