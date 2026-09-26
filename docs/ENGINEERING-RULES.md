# Felt — engineering rules

There were no formal coding rules before WP-38. This consolidates the
scattered ones (`00-implementer-context.md`, `DELEGATION.md`, review-doc
asides) and adds new ones from the five WP-38 architecture audits' smell
lists. Concrete and checkable — if you can't tell whether a change follows a
rule, the rule needs rewriting, not the change.

Applies to every repo under `E:\Felt` (felt-core, felt-animation,
felt-character-assets, felt-tray, felt-dashboard, felt-vision, felt-voice)
and the umbrella scripts. `00-implementer-context.md` still wins on
project-specific facts (machines, ports, deploy flow); this file is about
*how you write and land code*.

## 1. Structure

1. **One module = one job.** If you can't describe a file's responsibility in
   one sentence, it's doing too much. *Why:* `brain.py` (1080 LOC, 5 unrelated
   responsibilities), `server.py` (2095 LOC, 20 routes + ~15 loops), `main.gd`
   (2868 LOC, 10+ subsystems) and `app.py` (586 LOC god-class-in-a-file) are
   the four files every WP-38 audit called out first — this rule exists so a
   fifth doesn't grow the same way.
2. **Soft limit ~400 LOC per file, ~60 per function.** Hard review flag at
   800 LOC / 120 lines — a file or function past that gets a split proposal
   before more logic is added to it, not after.
3. **Don't reach into another module's `_private` helpers.** *Why:*
   `events.py` imports `brain.py`'s `_local_reply`/`_music_taste_context`/
   `_personality_prompt` directly — `events.py` is now silently coupled to
   `brain.py`'s internals staying stable, with no import-time signal that
   happened.
4. **No `global` mutable state — use a state object.** *Why:* felt-animation's
   `server.py` has 15 `global` statements across 14 functions; that's real
   mutable state with no owner, not constants. Pass an `AppState`/`Config`
   instance instead.
5. **Don't duplicate a pattern — factor it once it appears twice.** *Why:*
   the OAuth token-cache shape (`spotify_client.py`, `google_calendar.py`),
   the cloud→local fallback block (5 copies in `brain.py`/`events.py`), and
   the poll-loop shape (`_status_poll_loop`/`_music_poll_loop` in felt-tray)
   were each written twice with no shared helper before a third copy would
   have made it three.

## 2. Config

6. **Only via `config.py` (or `config.ts`), plus a `.env.example` that lists
   every key.** *Why:* felt-core's `.env.example` is missing the actual
   cloud-enable switch (`FELT_GEMINI_API_KEY`) and two whole integrations
   (Home Assistant, HP printer) — a fresh deployer can't discover they exist.
   felt-vision has no `.env`/`.env.example` at all.
7. **No hardcoded paths or addresses.** *Why:* `wardrobe.py`'s three absolute
   `E:/Felt/...` paths, `change_shirt`'s hardcoded `127.0.0.1:8421`, and
   `web_search`'s hardcoded SearXNG URL are the same mistake three times —
   every other sibling-service URL in the same codebase is a documented env
   setting with a default.
8. **Secrets only via env / sops — never printed, never committed.** Adding a
   setting means updating `config.py` **and** `.env.example` in the same
   commit; a secret's *name* goes in `.env.example`, never its value.

## 3. Interfaces

9. **Every relay message and HTTP endpoint gets documented in the owning
    README**, and a protocol change ships in the **same commit** as its doc
    update. *Why:* felt-character-assets' relay table is accurate today
    because this discipline was followed (one undocumented message found:
    `view_vsync`); felt-tray's README describing an overlay-launch path that
    hasn't existed since WP-08 is the counter-example — exactly the drift
    behind Mario's "black box" complaint.
10. **One source of truth for anything shared across repos** — tag classes,
    `SESSION_ID`, geometry math. *Why:* `SESSION_ID` is a hand-typed literal
    in both felt-tray and felt-dashboard; the tag-prefix classification rules
    exist as three independently maintained lists across two repos; a typo in
    any of them fails silently (a split chat history, a misclassified
    animation layer). Prefer: one repo defines it and the other reads/derives
    it, or a single checked-in shared constant both build against.

## 4. Tests

11. **New logic ships with tests.** No exceptions for "it's obviously right"
    — `plugins/change_shirt` had none and shipped dead and broken (wrong
    loading convention, wrong return type) with nothing to catch it.
12. **Tests are hermetic.** Never depend on the machine's real `.env`,
    running services, the real cursor position, or real ports. *Why:* two
    such bugs have already been found across the audits — this is not
    theoretical. Mock Win32/network calls (felt-tray's pattern is the
    reference); replay recorded cassettes for external APIs (felt-core's
    `tests/cassettes/` + `conftest.py --record-mode=once` pattern is the
    reference for anything hitting a real third-party API).
13. **Refactors carry a before/after proof.** Screenshot, measured
    walk/gait, or a re-run test suite with identical pass count — whatever
    the change could plausibly break, show it didn't. This is WP-35's own bar
    and applies to every god-file split (§ ranked list, WP-40).
14. **A gap in coverage gets named, not left implicit.** If a module is
    untested by design (e.g. `signals/afk.py`'s real Win32 input state,
    `signals/gpu.py`'s elevated hardware read), say so in a docstring or the
    test file — don't let "no test file" read as an oversight when it's a
    documented boundary.

## 5. Commits

15. **Conventional, WP-prefixed messages** (`WP-NN: what`, `fix(WP-NN): …`).
    Never a generic message like "Update Felt assets" — WP-18C's main.gd work
    existing only inside four such commits is why nobody could tell what
    shipped when.
16. **Refactors separate from behaviour changes.** A rename/split commit and
    a "changed what it does" commit are two commits, so a bad one can be
    reverted alone without losing the other.
17. **Asset moves/renames separate from code changes**, same reason — "so we
    can roll back some animation sorting bs" (Mario, after a mixed commit
    made exactly that impossible cleanly).
18. **Never `git add -A`, and never run `UpdateFelt.ps1` for a code change.**
    *Why:* `UpdateFelt.ps1` line 33 does a blanket `git add -A` + generic
    commit in `felt-character-assets` — no safelist, easily catches `.venv`,
    temp build output, or unrelated scratch files. Stage explicit paths.
19. **`[gemini-wip]` (or the delegated agent's tag) labels a non-Claude
    agent's commit** so provenance is visible in `git log` without opening
    the WP notes.
20. **Push to origin.** *Why:* the felt-core deploy loop `git reset --hard`s
    to `origin/main` on its own schedule; local-only commits get silently
    reverted (`clockmost-deploy-push-origin`). The 2026-09-24 audit found
    felt-animation 15 commits and the umbrella 22 commits unpushed — this is
    not hypothetical, it already happened.

## 6. Runtime and launch

21. **Never launch a `uv`-generated `.exe` shim.** Use `python -m <module>`
    against the signed venv `python.exe` instead. *Why:* Smart App Control
    blocks the shim the moment a `uv sync` regenerates its hash — this killed
    felt-tray for hours (dead since 01:38, undiagnosed) before `python -m
    felt_tray` became the standing launch method in `LaunchFelt.ps1`.
22. **Godot exports as the template exe plus a separate `.pck`**
    (`embed_pck=false`, `modify_resources=false`). *Why:* a freshly re-hashed
    unsigned exe gets blocked by SAC on every export; keeping the exe
    byte-identical to the signed stock template sidesteps that entirely.
23. **The overlay is single-instance.** Before launching `FeltOverlay.exe`,
    check whether something is already listening on the relay port and reuse
    it. *Why:* a felt-animation restart without this check spawned a second,
    visible avatar (fixed 2026-09-26) — verify with "1 overlay before and
    after a restart" whenever this path is touched.
24. **SAC-safe tooling generally**: prefer the signed interpreter/exe already
    on disk over a freshly built or freshly hashed binary for anything that
    runs unattended (scheduled tasks, hidden processes, launcher scripts).

## 7. Evidence

25. **Nothing is "done" without proof: tests plus live evidence.** A WP's
    "Notes from implementation" needs a `### Proof` section with exact file
    paths and counts, exact commands with raw (not paraphrased) output lines,
    and screenshots/renders where visual. *Why:* a 2026-09-22 session reported
    a feature "fully wired" that was never deployed and whose animation tags
    didn't exist — "it's a lie tho" (Mario). This rule is the direct fix.
26. **An honest "not done" list beats a hidden gap.** A `### Not done /
    unverified` section is not a confession of failure — it's the difference
    between a review that takes five minutes and one that has to rediscover
    everything from scratch.
27. **Only Mario ticks a WP after a live review.** Any agent — Claude
    included — sets status to `🔎 needs review`, never `✅`, on completion.
    Unit/smoke tests are not "live-verified"; presenting them as such is the
    exact failure mode the 2026-09-24 audit found across WP-09 through WP-19.

## 8. Privacy and product rules

28. **The capture blocklist runs before any pixels are grabbed** — by
    process/window metadata, never by asking a model to redact after the
    fact. Discord, all browsers, File Explorer, WhatsApp, Telegram, Phone
    Link, KeePassXC, banking. *Why:* the 2026-09-24 audit caught this rule
    being *violated* twice at once — the felt-tray window itself wasn't
    excluded (the uv-shim self-check never matched), and UWP apps (behind
    `ApplicationFrameHost`) got past the blocklist entirely. Both are now
    fixed and covered by tests; don't regress either.
29. **The cloud privacy line is fixed, not a judgment call per feature.**
    Fetching data always happens locally. Result *text* may be phrased by
    Gemini/Gemma. Email, calendar, alarms, shopping list, and music are
    cloud-OK. Documents/Obsidian, remembered facts, and phone location are
    never sent. Anything else goes through `privacy.py`'s classifier first,
    fail-closed.
30. **One voice.** Every sound she makes ends in the Kasane Teto RVC model.
    No other voice, no Gemini Live API — checked in `00-implementer-context.md`
    and reaffirmed after every TTS-engine change (Chatterbox-Turbo swap,
    Piper fallback) still routes through RVC.
31. **Never truly quiet by default.** No LLM decides to stay silent; screen
    reactions are always spoken, rate-limited only by deterministic
    cooldowns/dedupe/budgets. Voice ducks during calls; it doesn't hold back.
    A hush/quiet mode is fine **only when Mario triggers it** (hotkey, voice
    command, or a calendar-offered quiet mode he accepts) — never an
    autonomous decision.
32. **Godot is presentation only.** `main.gd` blends, plays, moves, and
    renders what it's told; every "what/when/why" decision lives in
    felt-animation or felt-core. A Godot change that adds a *decision*
    (not a response to one) is out of scope for that file.

## 9. Error handling

33. **No silent `except Exception: pass`.** Every catch either re-raises,
    degrades with a logged reason, or is narrowed to the specific exception
    expected. *Why:* `api.py`'s `chat_ws` handler swallows any error and just
    closes the socket with zero logging — the single worst offender found
    across ~50+ broad excepts audited; every other broad except at least logs
    something.
34. **Log with context** — what was being attempted, not just the exception
    class. A bare `except Exception:` with a bare `log.error(e)` is barely
    better than `pass` when three call sites share the same log line.
35. **Fail closed on privacy.** If the blocklist, the privacy classifier, or
    the cloud-safety check can't determine an answer, the safe answer is "no
    capture" / "no cloud call" / "local only" — never the permissive default.

## 10. Tooling

36. **ruff** (lint + format) on every Python repo (felt-core, felt-animation,
    felt-tray, felt-vision, felt-voice).
37. **ty (Astral; replaces pyright after WP-40)** (or basedpyright) for type checking on the same repos.
38. **pre-commit** wired to run both, plus whatever repo-specific hooks exist,
    before a commit lands.
39. **gdlint/gdformat** for `felt-character-assets`' GDScript.
40. **oxlint/oxfmt** for felt-dashboard (already enforced and green per its
    audit — the reference example for the others).
41. **Gitea Actions CI must be green** on every repo before merge — tests
    plus lint, matching felt-dashboard's existing `ci.yml` `smell` job as the
    template.

Wired up by WP-39 for felt-core/felt-animation/felt-tray/felt-vision (not
yet felt-voice — read-only access, see its own WP-39 notes) and
gdlint-only for felt-character-assets; see
`docs/plans/impl/WP-39-tooling.md` for the exact per-repo baselines
(pre-existing lint findings and pyright error counts this landed
without fixing) and CI status.

**Exact commands**, run from a repo root (felt-core/felt-animation/
felt-tray/felt-vision):

```sh
uv run ruff check              # lint
uv run ruff check --fix        # lint, safe autofixes only
uv run ruff format              # format
uv run ruff format --check      # format, check only (what CI runs)
uv run pyright                  # type check
uv run python scripts/check_pyright_baseline.py   # type check, gated on
                                                   # the recorded baseline
                                                   # (what CI runs)
pre-commit install              # one-time, wires .git/hooks/pre-commit
uv run pre-commit run --all-files   # run every hook without committing
```

felt-character-assets (from `felt-godot-overlay/`): `uvx --from
"gdtoolkit==4.*" gdlint .` (report-only — see its own CI job and
`gdlintrc`'s `excluded_directories`). **Never run `gdformat` on
`main.gd`/`props.gd`** until WP-35's split lands (it would clash with
the split and the `wp35-partial` stash).

A new setting always ships with its `.env.example` key in the **same**
commit (rule 6); the local `check-env-example` pre-commit hook (where
one exists — felt-core, felt-animation, felt-tray) fails the commit
otherwise.

## 11. Agents

Per the usefulness plan's accepted autonomy levels (2026-09-26):

42. **Agents open PRs; they never push to `main`.**
43. **CI (Gitea Actions) must pass**, and the ticket's Accept criteria must be
    met with evidence (§7), before anything merges.
44. **Normal tickets** get Claude's technical review, then Mario's final OK
    from the ticket itself.
45. **Trivial tickets** (docs, `.env.example` syncs, lint fixes) may
    auto-merge after CI plus Claude's review — reported in the feed, not
    silently landed.
46. **Never auto-merged, ever, regardless of ticket size:** privacy rules,
    secrets, deploys, the capture blocklist, or anything touching voice.
    Those always need Mario's explicit yes.
47. **A delegated agent stays inside its one WP** (`DELEGATION.md`) — no
    fixing unrelated things it noticed along the way; note them instead.
48. **A delegated agent never ticks its own WP** — status goes to
    `🔎 needs review`, same as rule 27, regardless of who or what did the work.


## Zero-error policy (2026-09-26)

- ty and ruff run at **zero errors**: no baselines.
- A genuine false positive gets an inline ignore with the rule name and a reason, never a blanket or per-file ignore.
- CI fails on any error.
