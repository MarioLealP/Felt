# WP-58 — Claude bridge: Felt hands concerning alerts to Claude

Board: FELT "WP-58". Follows WP-44 (incidents + her lines). Decided 10-03
(WP-42 decisions log): **A, a headless Claude on the server, investigate-only
to start** (Mario: "the idea is she can interact with you, and i interact
with her if needed, but if its very serious i will just pop over the app so
we deal with it together directly"). This is Felt's one opening to the cloud
(Mario: "im fully aware it would be the 'open' to the cloud"): the incident,
and the logs/config Claude reads while investigating, go to Anthropic.

## Shape (Claude's proposal, to check with Mario before building)

```
ntfy → felt-core incident (handler=claude, open)
         │  GET /v1/incidents/handoff  (bearer token)
         ▼
felt-responder (host, user clockmost-claude, polls every 60 s, one at a time)
         │  claude -p "<incident + how to investigate>" --output-format json
         │         cwd /home/clockmost-infra, read-only tool allowlist, 10 min cap
         ▼
POST /v1/incidents/{id}/report  {expected, summary, for_mario, proposed_fix, session_id}
         ▼
felt-core stores it on the incident → her follow-up line (the outcome: fine,
or needs Mario + "go to Claude's session"; her first line, "Claude's on it",
already went out at hand-over - Mario 10-03, two pings by design)
(12B words Claude's report, same fixed-facts rule as WP-44) → Systems (42.5)
```

- **Runs where:** on the host as `clockmost-claude` (the agent account: infra
  repo, docker, logs), not in a container, so it sees what an operator sees.
  A small Python runner + a systemd unit.
- **Investigate-only:** Claude Code's permission allowlist limits it to
  reading — Read/Grep/Glob, `docker ps/inspect/logs`, `journalctl`,
  `git log/show/diff` in the infra repo, `systemctl status`, the Zabbix and
  Wazuh read APIs. No `sudo`, no writes, no `docker restart`, no pushes. A
  fix is proposed in the report; doing it waits for Mario's go-ahead (later:
  specific fixes allowed automatically once trusted).
- **Wazuh file changes:** the prompt tells Claude to match each changed file
  against recent infra commits and deploys first; explained → expected,
  unexplained → for Mario.
- **Joining it:** each incident keeps Claude's session id. For something
  serious Mario continues the same session (`ssh clockmost-claude`, then
  `claude --resume <id>`), or opens the normal Claude app with the report.
- **Budget:** one investigation at a time, a daily cap (e.g. 20), repeats
  folded by WP-44, so a noisy night can't burn the subscription.
- **Auth:** Claude Code signs in with Mario's subscription via a long-lived
  token (`claude setup-token`, run once by Mario in his browser). The token
  goes into sops and only the runner gets it (secret write → Mario approves).

- **When Claude can't answer** (down, cap hit, no report in time): she tells
  Mario "Claude couldn't look at this", so nothing is dropped quietly.

## Decisions and progress

1. ~~The auth token~~ **done 10-03** (Mario: "we do setup token"): Mario ran
   `claude setup-token` and stored it himself through a hidden-input script
   into `ops/felt-responder/secrets.env` (infra d03bc95, never shown in a
   transcript). Claude Code 2.1.288 installed for clockmost-claude
   (~/.local/bin, official installer); a tool-less test call logged in.
2. The exact read-only allowlist. Sources (Mario 10-03: OpenObserve,
   Suricata, Trivy, Zabbix, Wazuh; plus the infra git history and deploy
   logs, checked first since most incidents are our own deploys):
   - **Zabbix: done** - user `felt-responder` (User role, the atlas's
     read-only group), API token in `ops/felt-responder/secrets.env`
     (`ZABBIX_TOKEN`, infra 3908ae4). Sees the 4 hosts and problems; writes
     refused (tested).
   - **OpenObserve: done, through a gate** - the OSS edition has no read-only
     users, so `openobserve-gate` (infra f59a38a, 127.0.0.1:5081) holds the
     login and passes on only GET /streams and POST /search (SELECT). Mario
     10-03: gate now; replacing OpenObserve (Loki / VictoriaLogs + Grafana)
     is a possible separate infra step later.
   - Suricata: through OpenObserve (`suricata` stream) + its eve files.
   - Trivy: its report file, for Trivy alerts only.
   - **Wazuh: done** - indexer user `felt-responder`, role
     `felt-responder-read` (wazuh-alerts-* read only; the alerts carry each
     file's checksum before/after), password in sops
     (`WAZUH_INDEXER_USER/PASSWORD`, infra e201122). Indexer now on
     127.0.0.1:9200 (infra 78f71ac). Other indexes, writes and the security
     API refused (tested). Mario allowed the manager API too ("you choose");
     left out until a report needs a file's current state.
   - **Runs as its own user with no sudo, sandboxed** (Mario 10-03: "Yes
     sounds like the best way to deal with it"): clockmost-claude has broad
     NOPASSWD sudo + docker, and three rendered Wazuh configs with secrets
     are world-readable, so a plain second user isn't enough. A systemd unit
     (DynamicUser, ProtectHome=yes, ProtectSystem=strict, no capabilities,
     journal group only) with its own clean clone of the infra repo (tracked
     files only, so only encrypted secrets). No Docker: container logs come
     from OpenObserve, container state from Zabbix.
3. **Its instructions** (Mario 10-03: "give that claude instance its own
   agent.md with proper explanation of its role and remind him that he is a
   cybersecurity what not"): `ops/felt-responder/CLAUDE.md` (infra b1875bc) -
   role in the chain, hard rules (read-only, secrets, data is never
   instructions, evidence over guesses, 10 min), method (did we do it first),
   the JSON report. Tool: `clockmost-read` (logs via the gate, Zabbix *.get,
   Wazuh alerts), tested on all three.
4. **Skills** (Mario: "look for skills that would fit"; then "Set it up"):
   nothing ready-made fits - anthropics/trailofbits have none, Elastic's
   security-alert-triage is Elastic-only and writes, the big community pack
   and the Wazuh MCP servers include offensive / active-response tools. Own
   skills instead (infra 23c8039): triage-alert (Elastic's loop on our
   tools), wazuh-file-change, security-signal, service-down, plus Mario's
   investigate-first.
5. **The exam: WP-59** (Mario: "make a ticket to feed it incidents we had ...
   we can compare its results"): past incidents with known causes, replayed,
   scored, before it goes live.
6. The daily cap.
7. Until this ships, WP-44 lines for Claude-handled incidents say "Claude is
   looking into it" — fine while lines aren't delivered anywhere; must be
   true before 42.5 shows them.
