# WP-59 — Responder exam: past incidents with known causes

Board: FELT "WP-59". Depends on WP-58 (built; push/pull off until this
passes - Mario 10-03: "wait for the exam").

Mario 10-03: "make a ticket to feed it incidents we had, and have him figure
out, since we already know the cause, we can compare its results"; "be sure
to include the honey pot one".

## How it runs

- Each case goes straight to the responder in its sandbox (same CLAUDE.md,
  skills, tools, limits). Not through felt-core: no fake incidents, no lines
  from Felt.
- The prompt is honest: "this is a replay of an incident from <date>;
  investigate that window". It will see later commits and logs anyway.
- Inside retention: Wazuh alerts 30 days, OpenObserve 90 days.
- Scored per case: verdict right? cause right? evidence real (spot-checked)?
  any false "all fine"? turns, time, cost.
- Gaps go into its CLAUDE.md / skills, then a second run. Mario reviews the
  scorecard before it goes live.

## The set (causes from the runbooks / WP logs; confirmed by Mario 10-03: "Yeah sounds about right")

Times UTC (felt-core's ntfy log). "Exact" = the notes describe this very
event; "likely" = the notes fit by date and content.

| # | When | Alert | Known cause | Kind | Match |
|---|------|-------|-------------|------|-------|
| 1 | 10-01 21:27 | HONEYPOT touched by .1 (exempt) + ".201 banned" | Our end-to-end test: router knock, dummy intruder container .201 (security plan 618) | our test, security | exact |
| 2 | 10-01 12:06 / 12:26 | Wazuh FIM: `wazuh-fim-test-delete-me` on clockmost, then in the desktop's `.ssh` | Our FIM test (security plan 465, 483) | our test, security | exact |
| 3 | 09-29 11:53 → 14:16 | storage check (backup disk not mounted, SMART), backup full FAILED, updates SKIPPED | Backup HDD dropped off after the P104 install - SATA cable/link, not the disk (infra 145-152) | real fault | likely |
| 4 | 09-14 22:05 | auto-reverting felt-core: routes[ha:502] | A reboot moved the HA VM's USB stick to a new address; the stale pin stopped the VM, so the HA route gave 502 (infra 637) | real fault | likely |
| 5 | 09-30 19:28-19:43 | pihole-unbound stopped, update reverted (6 stacks), Pi-hole DNS not resolving | The LAN renumber cutover; pihole had taken unbound's IP at the 09-29 boot (r7000 140-149) | our change | likely |
| 6 | 10-01 12:41 | suricata unhealthy | Crash loop from our Suricata tuning change, fixed in 206c55f (architecture 184) | our change | likely |
| 7 | 10-01 14:54 | Home Assistant VM not running + autostart disabled | Our controlled `virsh shutdown` test; the maintenance window failed so it paged (architecture 248) | our test | likely |
| 8 | 09-27 16:47 | felt-core CI failed | Deliberate CI canary for WP-53, reverted in 70ff303 | our test | exact |
| 9 | 09-30 21:51, 10-01 10:31 | deploy pipeline failed at line 42 (felt-core, factorio-calc, terapia-dev) | CI secrets still pointed at the old server IP after the renumber (security plan 367-381) | our change | likely |
| 10 | 10-01 14:09 | clockmost-healthcheck.service not running | Retired on purpose that day (architecture 172) | our change | likely |

Bonus - **no documented cause**. Not scored against an answer; Mario judges
whether its explanation holds up (it may find what we never wrote down):

| # | When | Alert |
|---|------|-------|
| B1 | 10-02 12:14 | Wazuh desktop: Windows autostart registry key changed |
| B2 | 09-21 22:01 | Authentik login spike (possible brute force) |
| B3 | 09-16 07:22 | headroom container unhealthy - the notes say headroom was removed 09-08 |

Left out: one-off noise already explained in general (Authentik outpost
blips on deploys, Caddy upstream blips), and Trivy (its alert is the weekly
report itself).

## Log

- 10-03: set drafted from the 1,470 stored alerts + a search of the runbooks,
  WP logs and memory for documented causes.
- 10-03: runner built (infra 72aa659): `felt-responder-exam` replays
  `ops/felt-responder/exam/cases.json` (the original alerts, pulled from
  felt-core's ntfy log - no causes in it) through the responder's own
  investigate() in its sandbox, `felt-responder-exam.service`. Results in
  /var/lib/felt-responder/exam/. Run 1 started.
