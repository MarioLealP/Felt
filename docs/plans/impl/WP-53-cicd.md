# WP-53: push to main = deployed (unified CI/CD)

**What:** every app we build from our own code deploys on its own after a
push to `main`: tested, built once, shipped, health-checked, and an alert on
any failure. Nothing else to do by hand.

**Why:** Mario, 2026-09-27: "every app that is deployed based on our git code,
should be automatically deployed seamless and raise an alert if it fails,
this should be just a push to master, nothing else". Also "keep it simple
stupid still the motto": we chose **option B (registry images) over k3s /
ArgoCD / OKD**.
- It keeps the August decision (compose stays on a single node; revisit k8s
  only with 3+ nodes).
- B already is GitOps-lite: the infra repo is the desired state and the
  deploy loop reconciles it. It's also forward-compatible if ArgoCD ever
  comes.

**Where:**
- the app repos: felt-core, clockmost-console, drive-rag, poe2rag,
  herosiege-filter, and the custom caddy image;
- clockmost-infra (compose image tags, the deploy loop);
- the Gitea container registry (`git.clockmost.com`);
- the Gitea Actions runner on clockmost (Linux).

## Design (option B)

1. **You push to `main`** in an app repo.
2. **CI job:** tests, ruff, and ty (the existing per-repo CI). If it fails
   → ntfy **urgent** ("felt-core CI failed on <sha>: <subject>").
3. **Build job** (`needs: ci`): `docker build` → push
   `git.clockmost.com/<owner>/<app>:<sha>`, plus a `:main` tag, to Gitea's
   container registry. If it fails → ntfy urgent.
4. **Promote job:** a bot commits a one-line tag bump
   (`image: …/<app>:<sha>`) in clockmost-infra's `projects/<app>/compose.yaml`
   and pushes. Then it **triggers the deploy right away** (a webhook or
   `systemctl start clockmost-deploy`, via a narrowly scoped mechanism)
   instead of waiting up to 10 min.
5. **Deploy loop (existing, unchanged core):** backup check → `compose pull`
   + `up -d` → health check + route probe → on failure, **auto-revert** the
   tag + ntfy **URGENT**. On success, one info-level ntfy ("felt-core
   <sha> live").
6. **The vendored `app/` copies are removed** from clockmost-infra once each
   app is on images. That ends the CRLF and stale-file problems.

**Secrets:**
- a registry push credential and an infra-repo write credential, each a
  Gitea token scoped to the minimum, stored as Actions secrets;
- **Mario creates them**, because the permission classifier blocks agents
  from creating credentials. The WP gives him exact UI steps. Jobs fail
  loudly if a secret is missing and never print one.

**Alerts:** every failing stage sends ntfy urgent, deduped per sha. It's
coordinated with WP-41's severity tiers, so success is info-level only and
never an alarm.

## Phases

1. **felt-core** (proves the pipeline end to end).
2. clockmost-console, drive-rag, poe2rag, herosiege-filter, caddy.
3. The Nitro5 felt-voice: a runner or agent there pulls and restarts
   `felt-voice.service` on push (not a container). Same alerts.
4. The desktop apps: self-update from Gitea releases, part of WP-34.
5. Note: nova-lemuria has its own pipeline. Check it against the same
   standard; don't migrate it blindly.

## Phase 1 notes (felt-core, 2026-09-27)

**Status:** accept #1 ✅. At 17:31 felt-core `bbf73c8` went live on its own
(`git.clockmost.com/benylin/felt-core:bbf73c83a469`, healthy) after a bare push.
- **#2 ✅.** Canary `66d6c9b`: the test failed, an urgent ntfy "felt-core CI
  failed" arrived, and nothing deployed. The canary was reverted in `70ff303`.
- **#3 accepted without a staged test.** Mario: "assume it's working". The
  17:01 run's spurious `auth:403` rollback exercised the real path: probe fail →
  ROLLBACK → last-good redeployed, plus an `auto-revert` infra commit.
- **#4 ✅.** The vendored `projects/felt-core/app/` was removed (infra
  `706ae1e`), along with a stale untracked plaintext `app/.env` from 09-11
  that nothing referenced. `00-implementer-context.md`'s old "copy into the
  vendored app" deploy steps were replaced with "push main".
- **Phase 1 is done.** Next is phase 2 (clockmost-console, drive-rag,
  poe2rag, herosiege-filter, caddy).

**How it's built vs. the design:**
- Build, push and promote are one CI job: a shared `deploy.sh` in public
  `Benylin/ci-workflows`, curl'd and run.
  - Gitea's cross-repo `workflow_call` failed silently, so it isn't used.
  - The secrets (registry token, infra deploy key, infra repo URL, known_hosts,
    optional ntfy) are user-level, so they're shared by every repo.
- Design step 4 ("trigger the deploy right away") was done by **polling**, not
  a push trigger (Mario chose option B, 2026-09-27). The deploy timer now runs
  every **1 min** (was 10). An idle tick is one local `git fetch`, then exit.
  - It needs no new credential and opens no CI→server path. It's the same
    pull model as ArgoCD and OpenShift image triggers.
  - The timer is now tracked as `ops/clockmost-deploy.timer`.
  - The loop picks the bump up on its next tick. It also exits silently if the git
  lock is busy; that happened once and cost one tick.
- The server pulls with `claude`'s `docker login` (a package:read token).

**Problems found and fixed on the way:**
1. **Split-horizon DNS.** The tunnelled names had Cloudflare AAAA records, and
   Cloudflare 403s the server itself. That broke `docker login` and the `auth`
   route probe, and the probe failure caused a spurious auto-revert.
   - Fix: the server's `/etc/hosts` pins git, auth, herosiege and twitch-* to
     `192.168.1.110`.
2. **CrowdSec appsec dropped registry layer uploads** as 403 ("request body
   exceeded maximum allowed size"). Through Cloudflare, the check timed out and
   returned a 500 instead.
   - Fix: the Caddyfile `@waf` exempts only `PATCH|PUT
     git.clockmost.com/v2/<owner>/<image>/blobs/uploads/<uuid>` (Mario: exact
     endpoint, no `/v2/*`).
3. **The server's infra checkout lost its Gitea token** (revoked), which
   silently stopped the deploy loop for every app.
   - Fix: it now uses an SSH deploy key with write access (`gitea-local` alias,
     `~/.ssh/id_ed25519_infra`).
4. **The first CI run "succeeded" by digest, but the push had failed.** The
   digest came from `docker build -q`. Check the registry or Gitea log, not the
   digest.

**Still to do (phase 1):**
- accept #2: a failing test → ntfy, and no deploy;
- accept #3: a broken health check → auto-revert and ntfy;
- confirm `NTFY_TOKEN` is set so failures actually alert;
- delete the vendored `projects/felt-core/app/`;
- optional: build the immediate deploy trigger.

## Accept

- A trivial commit pushed to felt-core `main` is live on the server with no
  manual step. The deploy log and a `/v1/...` response prove the new sha.
- A deliberately failing test → an ntfy urgent alert, and nothing deploys.
- A deliberately broken health check → auto-revert to the previous tag,
  plus an ntfy urgent alert.
- No app code is left vendored in clockmost-infra for migrated apps.

## Phase 2 notes (2026-10-02)
- **herosiege-filter:** the source was already in
  `Benylin/hero-siege-filter` (public; its branch is `master`).
  - Added `.gitea/workflows/ci.yml`: frontend fmt, lint, types and tests,
    then deploy. The deploy writes the `_build.json` stamp first.
  - Infra now runs `git.clockmost.com/benylin/herosiege-filter:<sha>`
    (`4b943d8`); the vendored `app/` was dropped (`9f0405a`).
  - Gotchas: `master` not `main`; a `printf '{"sha": ...}'` step needs a
    `run: |` block scalar (Gitea logs "ignore invalid workflow" and runs
    nothing).
- **drive-rag, poe2rag:** their only source was the copy vendored in infra
  (poe2-rag's original repo was lost in the desktop migration).
  - Created private `Benylin/drive-rag` and `Benylin/poe2rag` via
    push-to-create, from `git archive` of the vendored trees.
  - CI: an import check (no unit tests yet), then deploy.
  - Infra switched to the registry images (`540c229`) and dropped `app/`
    (`2bfaa54`). Both healthy, and felt-core reaches both.
- **Shared `deploy.sh`** got an optional `DOCKERFILE` (default `./Dockerfile`,
  `Benylin/ci-workflows` `9c05cad`). hero-siege-filter builds `app/Dockerfile`.
- **Why it matters:** on 10-02 00:46 a hand-merged Renovate bump to the
  vendored drive-rag/poe2rag deps failed its *local* build on the server
  (auto-revert `d80f57e`). Renovate should now run in the app repos instead.
  Not set up yet.
- **clockmost-console:** its project folder is empty; nothing to migrate.
- **caddy:** not migrated, pending Mario's call. Its "source" is stock Caddy
  plus three xcaddy plugins, no code of ours.
