# Changelog

All notable changes to the Tronexus stack. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2] - 2026-09-11

Theme: the stack should be up at any time. An update must never become an outage.

### Changed
- **Container images are pinned to stable tags.** Rolling tags (`latest`, `main`,
  `main-latest`) could deliver breaking releases overnight. Every pulled image now uses a
  tag that still receives patch and minor updates but never crosses a major boundary:
  `caddy:2`, `litellm:main-stable`, `open-webui:0.11`, `n8n:2.38.6`, `pgadmin4:9`,
  `watchtower:1.7.1`. `ollama` deliberately stays on `latest` (stable API, new models need
  the newest release). Open WebUI and n8n have no rolling tag and are bumped by hand.
- **Watchtower now updates all pulled images.** It ran with `WATCHTOWER_LABEL_ENABLE=true`
  while no service carried the label, so it updated nothing. With pinned tags it is safe
  to cover everything; locally built images are still never touched.
- **Installer OS update policy.** `install.sh` no longer overwrites the packaged
  `/etc/apt/apt.conf.d/50unattended-upgrades` (and restores it if a v0.1 install replaced
  it). Site policy lives in `52-tronexus`: security *and* regular (`-updates`) origins,
  unused-dependency removal, and an optional automatic reboot at 04:30 that only fires when
  a package requires it and no user is logged in. The wizard asks for it (default: yes).

### Added
- `monitor.sh`: dedicated SECURITY alert for unusual TLS handshake scan volume on port 443
  (`HANDSHAKE_SCAN_THRESHOLD` in `.env`); this noise is excluded from the generic error count.
- `AGENTS.md`: repository guide for AI tooling, including the image tag policy.
- Docs: *Updates & Reboots* section (three update layers, tag table, never-downgrade
  warning, upgrade notes from v0.1); *Dynamic IP / DDNS* guidance (one DDNS record, all
  hostnames as CNAMEs, Cloudflare 522 explained); *Mail spoofing* records (null MX, SPF,
  DMARC); FAQ entries for automatic reboots and the 522 symptom.

### Upgrade notes (v0.1 to v0.2)
1. Check the Open WebUI version you are running:
   `docker exec tronexus-openwebui sh -c 'grep -m1 version /app/package.json'`.
   If it is newer than 0.11, raise the tag in `docker-compose.yml` before pulling; an
   older image cannot start against a newer database.
2. `cd /opt/tronexus && git pull && docker compose pull && docker compose up -d`
3. Re-run `sudo bash scripts/install.sh` to restore the packaged unattended-upgrades file
   and write `52-tronexus`, or create that file by hand as documented.

## [0.1] - 2026-08

Initial alpha: Docker Compose stack (Caddy, Postgres, Redis, Ollama, LiteLLM, Open WebUI,
n8n, pgAdmin, Watchtower), custom Auth API, installer with Ubuntu hardening, Telegram
monitoring, website and docs.
