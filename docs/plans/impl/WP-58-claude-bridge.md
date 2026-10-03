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

## Privacy line

This is Felt's one opening to the cloud (Mario: "im fully aware it would be
the 'open' to the cloud"). What reaches Anthropic is everything the server's
Claude reads while investigating, sent through Mario's own Claude
subscription, so his claude.ai account's privacy settings govern how it's
kept.

**Goes out** (only while an incident is being investigated, or when Mario
joins a session):
- the incident: the alert titles and messages from ntfy;
- the infra repo as committed: compose files, configs, scripts, commit
  history. Secrets in it are sops-encrypted, so only ciphertext;
- log lines it searches: container logs, Suricata events and the router's
  syslog (OpenObserve, through the search-only gate). These can contain IP
  addresses, hostnames, URLs and request paths, and usernames tried on a
  login;
- Zabbix problems and metrics, and Wazuh's alert history (file paths,
  checksums, hostnames, user names on file changes);
- the host's journal, service status, disk / memory / socket summaries, and
  the latest Trivy report.

**Never goes out**, enforced by the sandbox rather than by asking nicely:
- decrypted secrets: `.env` files, sops output, keys and tokens (the
  sandbox hides `/home`, `/etc/age`, `/etc/clockmost`, `/root`,
  `/var/lib/docker`; the responder's own read-only logins are never printed);
- anything of Felt's: her chats with Mario, the diary, her memories, his
  email and calendar, screen captures, Spotify. They live in felt-core's
  database under `/home/docker`, which the sandbox can't see;
- photos (Immich), Drive, and any other app data - same place;
- the desktop's and the laptop's own files: only alerts *about* them.

**Mario controls it:** the kill switch in the app's settings turns it off
(nothing is handed over; her follow-up says Claude is switched off), and the
usage limits (70% session / 85% week) stop it when his own work needs the
plan.

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
6. **Built 10-03** (Mario: "Onwards"; token: "Yes I allow"):
   - felt-core aebb5c1: responder.py (claim, most urgent first, daily cap 20;
     report -> `handled` when nothing for Mario; missed after 15 min
     unclaimed / 20 min unreported), incident_api.py (POST
     /v1/incidents/handoff and /{id}/report, its own FELT_RESPONDER_TOKEN
     opens only those two), her follow-up line (outcome, or "Claude couldn't
     look"). 8eb9667: an incident Claude reported on never absorbs new
     alerts.
   - infra f212b94..ce8a683: felt-responder-run (one round per minute),
     felt-responder-prep (root prestep: clean clone, config from the repo,
     secrets for the round, files copied only when changed), the sandboxed
     unit + timer, settings.json (dontAsk + read allowlist),
     felt-responder-join (Mario resumes a session in the same sandbox).
   - **First live round = its own install**: Wazuh fired on the new unit
     files (incident 6). Round 1 ran no commands (git "dubious ownership" in
     the sandbox; `cd`/`git -C` forms refused) and still said, honestly,
     needs-mario / low confidence / what it couldn't check. Fixed; round 2:
     **expected**, every installed file matched the committed version by
     sha256, it found my short-lived debug unit on its own, medium
     confidence, 11 turns, 22 s, $0.16. Her follow-up: "Claude says it was
     just the new felt-responder being installed. No action needed unless you
     didn't run a test unit recently."
   - It also exposed a real bug: each round re-copied a watched file (an
     alert per round) and those folded into the incident it had already
     called fine - a genuine change in that window would have been absorbed.
     Both fixed.
   - **Limit by plan usage, not a count** (Mario 10-03: "instead of cost is
     capped, can we do the session % limit?"; "both numbers look good"): the
     runner skips when Claude's usage is past **70% of the 5-hour window or
     85% of the week** - his own work comes first; the incident is left
     unclaimed, so it's missed and her follow-up says Claude couldn't look.
     The percentages come from a tiny tool-less call's `rate_limit_event`
     (stream-json; undocumented - the docs only promise them to the status
     line), checked only when GET /v1/incidents/waiting says something
     waits. If the event ever disappears: logged, and felt-core's daily count
     cap (now 50, a runaway-loop net) is the limit. felt-core df4507e, infra
     61ffa4a. Usage at the time: 18% session, 74% week. Headless runs default
     to Sonnet.
   - **Push + pull, deadlines by urgency** (Mario 10-03: "just have a system
     send it to him directly no? ... both even, push and pull"; "Sounds
     great"): felt-core rewrites `data/responder-wake` when an incident starts
     waiting (on intake and on promotion) and `felt-responder.path` starts a
     round at once - a doorbell, no data, no open port; the timer every 2 min
     is the backup. A round works through everything waiting (max 5).
     Missed: unclaimed after 2 / 3 / 5 min (urgent / high / default+low), no
     report after 8 / 12 min; urgent runs capped at 6 min. felt-core 024fff6,
     infra d7ee7a0. Tested on a real one (incident 7, the new units tripping
     Wazuh): rang -> round started within 5 s -> usage 23% / 74% ok ->
     verdict **expected, high confidence**, files matched commit d7ee7a0
     byte for byte; 11 s, $0.08. Path unit switched off again after the test.
   - **Timer stays off until the WP-59 exam passes** (Mario 10-03: "wait for
     the exam"). Meanwhile Claude-handled incidents are marked missed after
     2-5 min and her follow-up truthfully says Claude couldn't look. Rounds
     can still be run by hand: `sudo systemctl start felt-responder.service`.
     Going live = `systemctl enable --now felt-responder.path
     felt-responder.timer`.
7. ~~Until this ships, "Claude is looking into it" isn't true~~ - true once
   the timer is on.

## Live

- 10-03 ~18:53 UTC: push + pull enabled after the WP-59 exam (Mario: "Sounds
  good, turn it on o7"). Her lines still go nowhere until 42.5; reports
  collect on the incidents.
