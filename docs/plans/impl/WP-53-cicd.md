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

## Accept

- A trivial commit pushed to felt-core `main` is live on the server with no
  manual step. The deploy log and a `/v1/...` response prove the new sha.
- A deliberately failing test → an ntfy urgent alert, and nothing deploys.
- A deliberately broken health check → auto-revert to the previous tag,
  plus an ntfy urgent alert.
- No app code is left vendored in clockmost-infra for migrated apps.
