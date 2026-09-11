# Tronexus Stack — Agent Guide

Context for AI tools working on this repo. **Tronexus** is a self-hosted, on-premise AI
stack that installs on a single Linux machine via Docker Compose (see `README.md`).

## Golden rules
- **All configuration is driven by `.env`.** Never hardcode values (domains, secrets,
  ports, thresholds) in `docker-compose.yml`, the Caddyfile, or scripts — read them from
  the environment. `.env.example` is the documented template; keep it in sync whenever you
  add a variable.
- **Container names follow `tronexus-<service>`.** Use these exact names in scripts
  (e.g. `docker logs tronexus-caddy`).
- On a deployed host the stack lives at **`/opt/tronexus/`** (repo copied there by
  `scripts/install.sh`); `monitor.sh` and backups reference that absolute path.

## Services (all on the `tronexus` Docker network)
| Container | Image | Purpose | Port |
|---|---|---|---|
| tronexus-caddy | caddy:2 | Reverse proxy + automatic TLS (Let's Encrypt) | 80, 443 |
| tronexus-auth | ./auth (build) | Custom auth API — Google OAuth + JWT | 8002 |
| tronexus-postgres | postgres:16 | Database (auth, apps) | internal |
| tronexus-redis | redis:7-alpine | Cache / rate-limiting | internal |
| tronexus-ollama | ollama/ollama:latest (deliberate) | Local LLM inference (NVIDIA GPU) | 11434 |
| tronexus-litellm | berriai/litellm:main-stable | Model gateway in front of Ollama/remote | 4000 |
| tronexus-openwebui | open-webui:0.11 (manual bump) | Main AI chat UI | 8080 |
| tronexus-n8n | n8nio/n8n:2.38.6 (manual bump) | Automation / workflows | 5678 |
| tronexus-pgadmin | dpage/pgadmin4:9 | DB admin UI | 80 |
| tronexus-watchtower | containrrr/watchtower:1.7.1 | Auto-updates within pinned tags (03:00) | — |

## Image tag policy
- **Stability over latest.** Every pulled image is pinned to a tag that receives
  patch/minor updates but never crosses a major boundary; Watchtower updates within
  that tag nightly. `open-webui` (minor tag) and `n8n` (exact) have no rolling tag and
  are bumped by hand after reading release notes; `ollama` stays on `latest` on purpose.
- Never reintroduce `latest`, `main` or `main-latest` for a pulled image. When adding a
  service, pick the major tag if the project publishes one, otherwise the exact version.

## Routing & TLS (`caddy/Caddyfile`)
- Hostnames derive from `${TRONEXUS_DOMAIN}`: apex → openwebui, `auth-api.` → auth,
  `n8n.` → n8n, `pgadmin.` → pgadmin.
- Caddy obtains certificates automatically via Let's Encrypt (HTTP/TLS-ALPN challenge);
  DNS must point at the host before first start. Auth is handled by the apps themselves
  (no forward-auth proxy).
- Public paths: n8n `/rest,/webhook,/webhook-test` and openwebui `/api,/ws,/static,/assets`.
- Gotcha: on an IPv4-only NAT that also publishes an AAAA record, Let's Encrypt may prefer
  IPv6 and fail issuance. A DNS-01 setup (via the domain's DNS provider) avoids this.

## Inference
- Local `tronexus-ollama` (GPU) by default, or remote via `OLLAMA_REMOTE=true` +
  `OLLAMA_REMOTE_URL`. `litellm` (`litellm/config.yaml`) is the gateway; openwebui talks to
  it at `http://tronexus-litellm:4000`. Startup model: `OLLAMA_DEFAULT_MODEL`.

## Monitoring (`monitor/monitor.sh`)
- Daily cron (`0 18 * * *`) → Telegram report with an Ollama-generated summary. Checks
  container health, per-container log errors (>50/24h), disk, fail2ban, backups, API-key
  expiry, apt security updates, remote-inference reachability, and TLS scan volume.
- **TLS scan volume:** public 443 gets constant background scanning that Caddy logs as
  `handshake error`. This noise is excluded from the generic error counter and instead
  trips a dedicated SECURITY alert only above **`HANDSHAKE_SCAN_THRESHOLD`** (`.env`,
  default 10000). Calibrate to ~2x the host's normal daily count:
  `docker logs --since 24h tronexus-caddy 2>&1 | grep -c "handshake error"`.

## Repo layout
- `auth/` — auth API source (built image) · `caddy/Caddyfile` — proxy + TLS
- `litellm/config.yaml` — model gateway · `monitor/monitor.sh` — daily report
- `scripts/install.sh` — installer (served at tronexus.dev/install.sh, deploys to /opt/tronexus)
- `website/` — marketing/docs site · `docs/` — documentation
- `docker-compose.yml` · `.env.example`

## Releasing
- Version lives in **`VERSION`** (plain `MAJOR.MINOR[.PATCH]`, no `v`). It is the single
  source: the installer prints it, and the website badge loads `/VERSION` at runtime (the
  deploy copies the file into the web root). Do not hardcode version numbers elsewhere.
- Release steps: bump `VERSION`, add a `CHANGELOG.md` section, commit, tag `v<VERSION>`,
  push branch and tag, deploy the website.

## Common tasks
- **Add a service:** define it in `docker-compose.yml` (name `tronexus-<x>`, `tronexus`
  network), add a Caddy block using `${TRONEXUS_DOMAIN}`, and document any new config in
  `.env.example`.
- **Add a config value:** put it in `.env.example` with a comment and read it via env —
  never hardcode.
