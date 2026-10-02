"""WP-37: the Felt board's tickets, in waterfall order (list order = board order).

Each ticket: key, title, state, labels, what, why, where, accept, depends,
evidence, spec. Done tickets keep it short (what/where/evidence/spec); open
ones carry the full What/Why/Where/Accept/Depends form Mario reads.
"""

SPEC = "https://git.clockmost.com/Benylin/Felt/src/branch/main/docs/plans/"
I = "impl/"
PLAN = SPEC + "felt-usefulness-plan-2026-09-26.md"


def done(key, title, where, evidence, spec, what=None, depends=()):
    return dict(key=key, title=title, state="Done", labels=["wp"], what=what or title,
                why=None, where=where, accept=[], depends=list(depends),
                evidence=evidence, spec=SPEC + spec)


TICKETS = [
    # ---- Phase 1: fix the reaction path
    done("WP-01", "felt-animation: unknown-tag freeze fix, file logs, test suite", "felt-animation",
         "Done (README index).", I + "WP-01-anim-tag-fix-logs-tests.md"),
    done("WP-02", "felt-core: screen observations out of chat history, privacy gap, always-spoken reactions",
         "felt-core", "Done (README index).", I + "WP-02-core-screen-context-rework.md"),
    done("WP-03", "felt-core quick wins: image-skill guard, parallel router/privacy, speech-style output",
         "felt-core", "Done (README index).", I + "WP-03-core-quick-wins.md", depends=["WP-02"]),
    done("WP-04", "Latency metrics end to end", "felt-core, felt-animation, felt-tray",
         "Done (README index).", I + "WP-04-latency-metrics.md", depends=["WP-03"]),
    # ---- Phase 2: the reaction pipeline
    done("WP-05", "Cloud model split + quota governor (since replaced by full-local WP-36)", "felt-core",
         "Done; superseded by WP-36 (no cloud AI).", I + "WP-05-cloud-models-governor.md", depends=["WP-04"]),
    done("WP-06", "Skill replies phrased by the model, short spoken style, weather cache", "felt-core",
         "Done (README index).", I + "WP-06-skill-replies-cloud.md", depends=["WP-05"]),
    done("WP-07", "Screen capture v2: per-window capture + blocklist + vision reactions", "felt-tray, felt-core",
         "Mario live-reviewed 09-26.", I + "WP-07-screen-capture-v2.md", depends=["WP-05"]),
    done("WP-08", "Playback in felt-animation: voice, lips and body in sync, stop", "felt-animation",
         "10-01 on evidence: 872 replies, sync p50 15 ms / p95 31 ms, /stop used 127x.",
         I + "WP-08-playback-sync-stop.md", depends=["WP-01"]),
    done("WP-09", "Speech bubble, call ducking, \"shut up\" hush", "felt-animation, felt-tray",
         "10-01 on evidence: bubble + hush fire; ducking seen live (-9 dB in a call).",
         I + "WP-09-bubble-ducking-hush.md", depends=["WP-08"]),
    done("WP-10", "Control keybinds + presence (hide / BRB / move / look / repeat / stop)", "felt-tray, felt-animation",
         "10-01 on evidence: hotkeys + presence events in daily use.", I + "WP-10-keybinds-presence.md",
         depends=["WP-09"]),
    # ---- Phase 3: face and body
    done("WP-11", "MSAA anti-aliasing", "felt-character-assets", "Mario live-reviewed 09-26.",
         I + "WP-11-15-face-body.md"),
    done("WP-12", "Face compositor + procedural face life", "felt-character-assets",
         "Mario live-reviewed 09-26.", I + "WP-11-15-face-body.md", depends=["WP-08"]),
    done("WP-13", "Listening pose + backchannel nods", "felt-animation, felt-character-assets",
         "10-01 on evidence: 254 listening poses, 136 nods in the log.", I + "WP-11-15-face-body.md",
         depends=["WP-08"]),
    done("WP-14", "Gaze: head/eyes follow the cursor, look at camera", "felt-character-assets",
         "Mario live-reviewed 09-26; iris leftover is on the polish pile.", I + "WP-11-15-face-body.md",
         depends=["WP-12"]),
    done("WP-15", "Mood x time-of-day system + reaction table + tone line", "felt-core, felt-animation",
         "Mario live-reviewed 09-26.", I + "WP-11-15-face-body.md", depends=["WP-07", "WP-12"]),
    # ---- Phase 4: context awareness
    done("WP-16", "Music: beat sync, Spotify now-playing, LRCLIB lyrics", "felt-animation, felt-core",
         "10-01 on evidence: beat sync, now-playing and lyrics all active.", I + "WP-16-17-context.md",
         depends=["WP-15"]),
    done("WP-17", "Signals: game start/stop, AFK, GPU heat, rage-click rate, call energy", "felt-animation",
         "10-01: all signals fire. GPU heat now reads AMD ADL (82 C live in PoE2); hot = 85 C -> a cool-off drink.",
         I + "WP-16-17-context.md", depends=["WP-15"]),
    # ---- Phase 5: assets and the desktop world
    done("WP-18", "Animation assets: Animset Pro triage + downloads + walking fix", "felt-character-assets",
         "Mario live-reviewed 09-26; walk leftovers on the polish pile.", I + "WP-18-23-assets-world.md",
         depends=["WP-01"]),
    done("WP-20", "AnimationTree layering", "felt-character-assets",
         "Mario live-reviewed 09-26: good enough.", I + "WP-18-23-assets-world.md", depends=["WP-14", "WP-18"]),
    done("WP-21", "Props system, chest, dissolve FX, clean-house key", "felt-character-assets, felt-animation",
         "Mario 09-26: done, a bit janky; jank is on the polish pile.", I + "WP-18-23-assets-world.md",
         depends=["WP-20"]),
    done("WP-22", "Follow-window overlay + multi-monitor + supersampling", "felt-character-assets, felt-tray",
         "Mario 09-26: working; gaming fps is on the polish pile (performance pass).",
         I + "WP-18-23-assets-world.md", depends=["WP-20"]),
    done("WP-23", "Desktop world: platforms, ledges, falls, riding windows", "felt-character-assets, felt-tray",
         "09-27: all 5 slices; slice 5 good enough after the seated-loop fix b9e4bba.",
         I + "WP-18-23-assets-world.md", depends=["WP-22", "WP-21"]),
    done("WP-24", "Repo hygiene (AnimToVrmaConverter junk, dead code, felt-vision docs)", "all repos",
         "09-27.", I + "WP-24-hygiene.md"),
    # ---- Phase 6: life features
    done("WP-25", "Proactive channel: server -> desktop pushes", "felt-core, felt-tray",
         "09-27 live: claimed in 0.4 s, expired pushes never delivered.", I + "WP-25-31-life-features.md",
         depends=["WP-09"]),
    done("WP-26", "The diary: day-to-day continuity", "felt-core",
         "09-30: entries for 09-27 and 09-28 written the next mornings, 5 self-memories formed.",
         I + "WP-25-31-life-features.md", depends=["WP-07", "WP-15", "WP-25"]),
    done("WP-27", "Wardrobe: outfit definitions, triggers, model swap", "felt-animation, felt-character-assets",
         "Tier C live 09-30 (16 VRM outfits + 10 recolours; \"all perfect\"). Generated outfits parked on the polish pile.",
         I + "WP-25-31-life-features.md", depends=["WP-33", "WP-21", "WP-15"]),
    done("WP-28", "Screen-matched lighting + contact shadow", "felt-character-assets",
         "10-02 accepted without live check (Mario: \"I'm not home, so visual and audio tests I'm not able to Chek\").",
         I + "WP-25-31-life-features.md", depends=["WP-07"]),
    done("WP-29", "Path of Exile 2 companion (loot prices, wiki RAG)", "felt-tray, felt-animation, felt-core",
         "10-02: EE2 key / Ctrl+C -> she prices it; verified end to end with a Divine Orb. Mario to try a real unique.",
         I + "WP-25-31-life-features.md", depends=["WP-07", "WP-06"]),
    done("WP-30", "Hobbies while Mario is AFK", "felt-animation",
         "10-02 on evidence: napping, tidying, reading in the log. Hobby clips on the polish pile.",
         I + "WP-25-31-life-features.md", depends=["WP-21", "WP-17", "WP-26"]),
    done("WP-31", "Calendar heads-up", "felt-core",
         "10-02 accepted without live check; dry run reached Google Calendar.", I + "WP-25-31-life-features.md",
         depends=["WP-25"]),
    done("WP-32", "Wardrobe Tier A: accessories", "felt-animation, felt-character-assets",
         "10-01: 12 accessories live with Mario's fits.", I + "WP-32-33-wardrobe-automation.md"),
    done("WP-33", "Wardrobe Tier A: a new tee every day", "tools/outfits, felt-animation",
         "10-01: 18 approved tees (graphics + patterns, no text ever). Seasonal weighting on the polish pile.",
         I + "WP-32-33-wardrobe-automation.md"),
    done("WP-35", "Animation Studio: browse/play/scrub clips, combos, mark keep/broken", "felt-character-assets",
         "10-02 accepted without live check.", I + "WP-35-animation-studio.md", depends=["WP-20"]),
    done("WP-36", "Local brain: llama.cpp felt-llm (Gemma 4 12B QAT) on the P104, full local", "felt-core, clockmost",
         "10-02: days of real use; every caller local, drive-rag included.", I + "WP-36-llamacpp.md"),
    # ---- Usefulness plan, done part
    done("WP-38", "Architecture audit: system map + engineering rules + cleanup list", "docs, all repos",
         "10-01: the cleanup list shipped through WP-39/40; ARCHITECTURE.md in use.", I + "WP-38-architecture-audit.md"),
    done("WP-39", "Repo tooling: ruff/ty, pre-commit, Gitea Actions CI", "felt-core, felt-animation, felt-tray, felt-vision",
         "10-01: CI runs and deploys; Mario: \"CI is fixed\".", I + "WP-39-tooling.md", depends=["WP-38"]),
    done("WP-40", "God-file splits: felt-animation server.py, felt-core brain.py, felt-tray", "felt-animation, felt-core, felt-tray",
         "10-01: split modules live for a week; HushState fix shipped.", I + "WP-40-god-file-splits.md",
         depends=["WP-39"]),
    done("WP-53", "Push to main = deployed (CI -> registry -> tag bump -> deploy loop)", "ci-workflows, clockmost-infra, app repos",
         "Phase 1 felt-core (09-27); phase 2 10-02: herosiege-filter, drive-rag, poe2rag build in CI. Caddy stays local "
         "(Mario: \"Do not touch caddy\"). Nitro5 + desktop phases move into WP-34.",
         I + "WP-53-cicd.md", depends=["WP-39"]),
    done("WP-54", "Voice v2: IndexTTS-2.5 -> RVC with moods, sentence streaming", "Nitro5 felt-voice, felt-core",
         "10-02 accepted without live check; serving every reply since 09-29.", I + "WP-54-voice-v2.md"),
    done("WP-55", "felt-core API auth (token) over Caddy HTTPS, close :8420", "felt-core, clockmost-infra, clients",
         "10-01: token enforced, :8420 closed, /shopping-list behind SSO. Phone check pending.", I + "WP-55-api-auth.md"),
    done("WP-56", "Config leftovers from the security pass", "felt-core, drive-rag, clockmost-infra",
         "10-01: drive-rag on local felt-llm, SearXNG deployed. Wazuh triage moved to WP-43.",
         I + "WP-56-config-leftovers.md"),

    # ---- Open, in order
    dict(key="WP-37", title="The board: Plane + ticket template + WP migration + Felt read-only board skill",
         state="In progress", labels=["wp"],
         what="This board. Every WP is a short ticket (What / Why / Where / Accept / Depends / Evidence) that "
              "links to its long spec. The README status table is generated from the board, a small metrics "
              "script reports cycle time and bounces, and Felt can read the board (never move cards).",
         why="Mario: \"gitea one is plenty\" -> Gitea couldn't be scripted, so Plane (open source, free): "
             "\"Plane sounds good\". \"I don't wanna parse through them, but I'm totally fine parsing through a ticket\". "
             "\"she should have overview of the gitea board also\".",
         where="plane.clockmost.com (clockmost-infra projects/plane), Felt docs/plans/impl/README.md, felt-core skill",
         accept=["Plane live, VPN-only, Sign in with Gitea (SSO)",
                 "One waterfall board with every WP + the polish pile",
                 "README status table generated from the board",
                 "Felt answers \"what's in progress / waiting for me / next?\" read-only",
                 "Metrics script: cycle time, review bounces, failed-live, follow-ups"],
         depends=[], evidence="10-02: Plane live, Mario logged in (\"Works\"); board built.", spec=PLAN),
    dict(key="WP-41", title="ntfy alert hygiene on clockmost: severity tiers, expected-event suppression, dedupe",
         state="Ready", labels=["wp", "server"],
         what="Make the server's ntfy alerts trustworthy before Felt listens to them: urgent / warn / info tiers "
              "across every clockmost-notify.sh caller, silence expected events (deploy-caused reloads and "
              "restarts, the Monday reboot, prune windows), and dedupe/cooldown flapping checks.",
         why="Mario: \"they are a bit too trigger happy, since caddy update cuz we getting a new container up is "
             "basically the same as a world ending event\".",
         where="clockmost-infra (clockmost-notify.sh + callers: healthcheck, deploy, backup, prune, maintenance)",
         accept=["Every alert has a tier", "A normal deploy sends no urgent alert",
                 "A flapping check alerts once per cooldown", "Check first what the infra session already did"],
         depends=[], evidence="", spec=PLAN),
    dict(key="WP-42", title="Felt app on clockmost behind SSO: Chat / Feed / Daily briefs / Diary",
         state="Backlog", labels=["wp"],
         what="A web app served from clockmost next to felt-core, behind SSO. Separate logs: Chat (full history + "
              "typing to her), Feed (unprompted remarks, email mentions, alerts; read/unread, dismiss/snooze/not "
              "interested), Daily briefs, Diary. Desktop Felt window and phone are just viewers. Editable lists "
              "(game news, noise rules) live here.",
         why="Mario: \"we might need an actual app style for her, cuz I might miss her saying that but would come in "
             "handy to see written\". \"server holds the app, desktop and phone for presentation layer\".",
         where="felt-dashboard (React), felt-core store/API, clockmost Caddy + SSO",
         accept=["Opens on desktop and phone with SSO", "Chat, Feed, Briefs, Diary tabs with real data",
                 "Feed read/unread + actions work", "Nothing new goes to the cloud"],
         depends=["WP-37"], evidence="", spec=PLAN),
    dict(key="WP-43", title="Email: noise deny-list, ambient mentions, tell-me-more, Gmail drafts (never send)",
         state="Backlog", labels=["wp"],
         what="Every email that isn't noise becomes one ambient \"btw\" mention (once, ~1/hour max, never over call "
              "talk). Skip Promotions/Social and an editable noise list. \"Tell me more\" summarises, \"draft a "
              "reply\" saves a Gmail draft; she never sends. Plus Wazuh triage (from WP-56 item 5).",
         why="Mario: \"it's not what makes it worth interrupting, it's what doesn't … the alerts can be part of her "
             "ambience loop, hey btw have you checked that email from … Patreon about ZYX\".",
         where="felt-core (email_watcher, ambient loop), Felt app feed",
         accept=["Noise senders never mentioned", "Each other email mentioned once", "Drafts saved, never sent",
                 "\"I don't care about X emails\" adds to the noise list"],
         depends=["WP-42"], evidence="", spec=PLAN),
    dict(key="WP-44", title="Server and PC care via ntfy (urgent -> spoken, warn -> ambient, info -> never)",
         state="Backlog", labels=["wp"],
         what="Felt subscribes to the clockmost ntfy topics: urgent becomes a prompt spoken line, warn a casual "
              "\"btw\", info is never mentioned. Disk-space and backup checks feed ntfy instead of her polling. "
              "Chocolatey notices skipped (it auto-patches).",
         why="Mario: \"She can actually react based on ntfy\".",
         where="felt-core (ntfy consumer), clockmost-infra + desktop checks feeding ntfy",
         accept=["Urgent spoken promptly", "Warn mentioned once, casually", "Info never mentioned",
                 "Disk + backup checks publish to ntfy"],
         depends=["WP-41", "WP-42"], evidence="", spec=PLAN),
    dict(key="WP-45", title="Morning brief, spoken + written card",
         state="Backlog", labels=["wp"],
         what="About 20 s once a day on the first activity after the night: today's calendar and weather, the count "
              "of noteworthy emails, reminders, overnight urgent/warn alerts, and the board (\"N tickets need your "
              "review\"). Also a written card in the app.",
         why="Mario said yes to a spoken + written morning brief (2026-09-26 decision).",
         where="felt-core, Felt app (Daily briefs)",
         accept=["Fires once on the first morning activity", "~20 s spoken", "Card archived in the app"],
         depends=["WP-42", "WP-43"], evidence="", spec=PLAN),
    dict(key="WP-46", title="Reminders (time / event / recurring) + quiet mode",
         state="Backlog", labels=["wp"],
         what="Reminders by phrasing: time-based (\"in 20 min\"), event-based (\"after this match\" -> game stop, "
              "\"when I'm back\" -> AFK end), recurring -> Google Calendar events. Quiet mode: she disappears "
              "entirely and goes fully silent (voice, tray or hotkey; timer), everything goes to the feed, one "
              "catch-up line after. Calendar-aware: offers quiet mode 5 min before an event.",
         why="Mario: \"a dedicated go quiet so I can have an interview or something is cool … disappear entirely, "
             "also use calendar for this\".",
         where="felt-core, felt-animation (hide), felt-tray (tray item/hotkey), Google Calendar",
         accept=["All three reminder kinds fire", "Quiet mode hides her + props, fully silent",
                 "Catch-up line after", "Calendar offer before events"],
         depends=["WP-42"], evidence="", spec=PLAN),
    dict(key="WP-47", title="Home Assistant controls: lights + fan allowlist, asked-only",
         state="Ready", labels=["wp"],
         what="Voice/text control of an entity allowlist (today: lights and a fan) plus state questions (\"is the fan "
              "on?\"). The allowlist grows as devices are added; security-type entities need an explicit yes. No "
              "autonomous presence/game tie-ins, no home-alert relaying.",
         why="Mario: small, asked-only, extensible; he is slowly buying more devices (2026-09-26 decision).",
         where="felt-core skill, HA long-lived token in sops, ha.clockmost.com",
         accept=["Lights + fan controllable by voice", "State questions answered",
                 "Anything off the allowlist refused"],
         depends=[], evidence="", spec=PLAN),
    dict(key="WP-48", title="Spotify controls + DJ mode (local picks)",
         state="Ready", labels=["wp"],
         what="Controls: skip/back/pause/volume, \"what's this song\", \"save this song\", never on her own. DJ mode "
              "on Mario's word: she runs the queue from taste memory x time x mood, optional short DJ lines, "
              "\"not this\" / \"more like this\" feed taste memory. Picks come from felt-llm (local), Spotify only plays.",
         why="Mario: \"play whatever you want and however you want\"; Spotify recommendations: \"they're always the "
             "same\" (picks were Gemini; now local per full-local).",
         where="felt-core (Spotify client, taste memory), felt-llm",
         accept=["Controls work by voice", "DJ mode queues and avoids repeats", "Stops on stop/pause/hush"],
         depends=["WP-16"], evidence="", spec=PLAN),
    dict(key="WP-49", title="Game companions: ask-anything lookup + news tracker (FFXIV, Endfield, PoE)",
         state="Backlog", labels=["wp"],
         what="Generic ask-anything web/wiki lookup on the game being played, plus a news tracker for FFXIV, "
              "Arknights Endfield and Path of Exile from official feeds: new items become one ambient mention + a "
              "feed card; maintenance/event times can become reminders. Watched-games list editable in the app.",
         why="Mario: both, plus game news; \"whatever else I remember later\".",
         where="felt-core skills, SearXNG, Felt app (watched-games list)",
         accept=["A question about the current game gets an answer", "New patch notes mentioned once",
                 "Watched-games list editable in the app"],
         depends=["WP-42"], evidence="", spec=PLAN),
    dict(key="WP-50", title="Agents infra: 9router / smartrouter / OpenHands inventory -> one gateway + GPU sizing",
         state="Backlog", labels=["wp", "server"],
         what="Inventory what each runs and who calls it, check the side projects, then keep/merge/retire toward one "
              "OpenAI-compatible gateway in front of felt-llm. Include a VRAM sizing recommendation for a possible "
              "server GPU + PSU.",
         why="Mario: both routers \"only have gemini authed, was for some side projects\".",
         where="clockmost-infra (ninerouter, smartrouter, openhands stacks)",
         accept=["Inventory written", "Keep/merge/retire decision per tool with Mario",
                 "GPU sizing numbers"],
         depends=["WP-36"], evidence="", spec=PLAN),
    dict(key="WP-51", title="Local coding-agent benchmark on backlog tasks",
         state="Backlog", labels=["wp"],
         what="Benchmark local coding agents (OpenHands, aider, OpenCode, Cline, goose …) with models that fit our "
              "hardware on real backlog tasks (hygiene, a test, a small refactor, docs, .env.example sync). Measure "
              "pass rate, time and fix-ups.",
         why="Routine coding grind moves off Claude onto local agents (Track D goal).",
         where="server / Nitro5, Gitea branches",
         accept=["Each candidate run on the same task set", "Pass rate + time table", "A recommendation"],
         depends=["WP-50", "WP-39"], evidence="", spec=PLAN),
    dict(key="WP-52", title="Felt as mastermind: agent-ok dispatch, PRs + CI, autonomy levels, kill switch",
         state="Backlog", labels=["wp"],
         what="Only agent-ok tickets are agent work. Agents open PRs, never push to main; CI must pass. Trivial "
              "tickets auto-merge after CI + Claude review; normal ones need Mario's OK; privacy/secrets/deploys/"
              "blocklist/voice never auto-merge. Felt dispatches, tracks and reports in her voice and the feed. "
              "Sandboxed, no secrets, quotas, audit log, tray kill switch. No fun mode.",
         why="Mario: \"Sounds about right I like it\"; fun mode dropped: \"let's not waste electricity like that, we "
             "keep it purely practical\".",
         where="felt-core, the board, Gitea, agent runners",
         accept=["An agent-ok ticket becomes a PR without help", "Felt reports it in the feed",
                 "Kill switch stops a run"],
         depends=["WP-51", "WP-42"], evidence="", spec=PLAN),
    dict(key="WP-19", title="Sound deep dive: better non-verbals (laughs, giggles, breaths)",
         state="Backlog", labels=["wp"],
         what="WP-19 is accepted for now (38 keepers live). After every other WP: look at alternative sources for "
              "laughs/giggles, a converter that keeps breaths, and ooh / mm-hm mappings.",
         why="Mario accepted the current batch \"for now\" and asked for a deep dive on alternatives once every other "
             "WP is done.",
         where="Nitro5 voice, felt-animation sound table",
         accept=["Alternatives compared", "Mario picks in the review app", "New keepers live"],
         depends=[], evidence="09-26: 38 keepers live, sync OK.", spec=SPEC + I + "WP-18-23-assets-world.md"),
    dict(key="WP-57", title="Felt learns PoE2 pricing on the side",
         state="Parked", labels=["wp"],
         what="Phase 1 (live): every price check is logged. Phase 2: silent guesses -> a scorecard -> a trial as the "
              "price person. Parked until a pricing session at home with an item pool.",
         why="Mario: \"can we have EE2 its own thing, and have her learn pricing on the side so at some point, can try "
             "her being the full price person\"; \"once I'm home, we go around the shop and we price stuff\".",
         where="felt-core (poe_item events, pricing), felt-tray clipboard watcher",
         accept=["Item pool built with Mario", "Scorecard of her guesses vs real prices", "Trial run"],
         depends=["WP-29"], evidence="Phase 1 collecting since 10-02.", spec=SPEC + I + "WP-57-poe-pricing-learner.md"),
    dict(key="TIER-C", title="Mario's VRoid outfit checklist (pajamas, hoodie, rain, winter, Halloween by mid-Oct)",
         state="Backlog", labels=["mario"],
         what="Mario's own outfit list for VRoid; each finished outfit gets wired like the existing Tier C outfits.",
         why="Mario's checklist.", where="VRoid Studio, felt-character-assets",
         accept=["Halloween outfit by mid-October"], depends=[], evidence="",
         spec=SPEC + I + "MARIO-vroid-outfits.md"),
    dict(key="WP-34", title="Packaging: one clean install per device (last)",
         state="Backlog", labels=["wp"],
         what="Desktop = one tray app supervising everything (no console, PowerShell or scheduled tasks); Nitro5 = "
              "one install + model manifest; server bootstrap; FRESH-INSTALL.md. Includes WP-53 phases 3-4 (Nitro5 "
              "voice and desktop apps deploy from CI).",
         why="Bundles everything, so it goes last (Mario 2026-09-26).",
         where="felt-tray, Nitro5, clockmost, docs",
         accept=["A fresh install per device from the doc", "First decision: Smart App Control / code signing"],
         depends=[], evidence="", spec=SPEC + I + "WP-34-packaging.md"),
]

POLISH = "Polish pile"
PB = SPEC + I + "POLISH-BACKLOG.md"


def polish(key, title, what, why, where):
    return dict(key=key, title=title, state=POLISH, labels=["polish"], what=what, why=why, where=where,
                accept=[], depends=[], evidence="", spec=PB)


TICKETS += [
    polish("POL-1", "Walk cycle still slightly wonky",
           "Slight lean into the stride, rear-foot flick, ~0.13 m/s planted-foot slip; walk/run start and stop clips "
           "off. Try a cleaner clip, foot IK / foot locking, in-place start/stop, per-style speeds.",
           "Mario: \"still slightly wonky but much better, leave it be for polish one day\".", "felt-character-assets"),
    polish("POL-2", "Irises slightly off when looking up",
           "Eye pitch capped at 4 deg up / 7 down. Check whether 4 is too tight, or drive from the VRM's lookAt range.",
           "Mario: \"she tracks fine, just slightly off on iris upwards\".", "felt-character-assets"),
    polish("POL-3", "Props are a bit janky",
           "Grip offsets per prop, chair seat hidden by armrests, kicked props only move sideways, umbrella carried "
           "closed, throw-into-chest and carry-back tidy untested.",
           "Mario: \"bit on the jank side but solid progress… mark as done but mark to be polished way later\".",
           "felt-character-assets"),
    polish("POL-4", "Performance pass: benchmark everything, starting with gaming fps",
           "Overlay drops to 1-13 fps while a game runs. Levers: render cheaper during games, vsync off on the side "
           "window, skip the side window when empty. Also benchmark voice latency, felt-animation CPU, Nitro5 VRAM. "
           "One repeatable benchmark script.",
           "Mario: \"we need to run some performance benchmarks i think in general\".",
           "felt-character-assets, felt-animation, Nitro5"),
    polish("POL-5", "Hobby clips: reading, napping, doodling",
           "Reading uses the seated idle, napping has no lying-down clip, doodling left out (no sketchbook prop).",
           "From WP-30.", "felt-character-assets"),
    polish("POL-6", "Seasonal tee weighting",
           "roll_tee picks uniformly, so pumpkin tees can come up in June. Tag tees by season, weight out-of-season to zero.",
           "Mario: \"keep the other on polish\".", "felt-animation wardrobe"),
    polish("POL-7", "Generated mix-and-match outfits",
           "Parked from WP-27: shoe-as-base feet fix, outfit-level styling.", "From WP-27.",
           "tools/outfits, felt-animation"),
    polish("POL-8", "ComfyUI on the Nitro5 (parked)",
           "felt-comfyui is a user service without linger, so generate_image mostly fails. Fix: loginctl enable-linger "
           "(mind VRAM contention with voice).",
           "Mario: \"We can park comfyui I don't care enough about it tbh\".", "Nitro5"),
]

LATER = [
    ("IDEA-1", "Automatic memory (review doc D-2)"),
    ("IDEA-2", "Hands-free voice (review doc D-6)"),
    ("IDEA-3", "Second-monitor-specific polish"),
]
TICKETS += [dict(key=k, title=t, state="Backlog", labels=["idea"],
                 what=t + ". Not packaged as a WP yet (README \"Not packaged yet\").", why=None,
                 where="", accept=[], depends=[], evidence="", spec=SPEC + "felt-review-2026-09-22.md")
            for k, t in LATER]
