# Tronexus

**A self-hosted, on-premise AI stack you can install on a single Linux machine in under an hour.**

Tronexus is an opinionated, production-grade AI infrastructure stack built for developers, tinkerers, and small teams who want to run their own AI services — without depending on cloud providers, paying per token, or compromising on privacy.

Named after the foundational computing architecture of the Federation, Tronexus is the nexus your self-hosted AI stack connects through.

---

## Version
Alpha release v0.1

Please report any issues or bugs, I will be more than happy to help you.

## What it is

A curated, pre-integrated collection of open source services that work together out of the box:

- **Local LLM inference** via Ollama — run models on your own GPU or CPU
- **AI chat interface** via Open WebUI — full-featured, multi-model, multi-user
- **LLM routing and proxy** via LiteLLM — unified API across local and remote models
- **Workflow automation** via n8n — AI-powered automations without writing code
- **Authentication** via Tronexus Auth — Google OAuth, JWT tokens, API keys, role management
- **Reverse proxy and TLS** via Caddy — automatic HTTPS, zero config
- **Monitoring and alerts** via a built-in monitor script — Telegram notifications, container health, disk, security
- **Hardened Ubuntu base** — fail2ban, UFW, SSH hardening, automatic security updates, and audited service configuration out of the box
- **Remote inference support** — connect a separate GPU machine as your inference backend

Everything runs in Docker. Everything is configured through a single `.env` file.

---

## Hardware requirements

| Component | Minimum |
|-----------|---------|
| OS | Ubuntu 24.04 LTS |
| RAM | 15 GB |
| GPU VRAM | 8 GB (NVIDIA) |
| Storage | 256 GB SSD |
| Network | Any broadband connection |

No cloud account required. No API keys required to get started. DNS/DDNS is optional.

A second machine can be used as a dedicated inference server — Tronexus supports remote Ollama endpoints out of the box.

---

## Quick start

> Full installer coming soon. For now, clone and configure manually.

```bash
git clone https://github.com/Tronexus/tronexus-stack
cd tronexus-stack
cp .env.example .env
# Edit .env with your settings
docker compose up -d
```

Detailed setup guide: [tronexus.dev](https://tronexus.dev)

---

## Architecture

```
                        ┌─────────────────────┐
                        │      Caddy (TLS)     │
                        └────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐      ┌───────▼──────┐      ┌───────▼──────┐
   │  Open WebUI │      │     n8n      │      │ Tronexus Auth│
   └──────┬──────┘      └───────┬──────┘      └───────┬──────┘
          │                      │                      │
   ┌──────▼──────────────────────▼──────┐      ┌───────▼──────┐
   │              LiteLLM              │      │   Postgres    │
   └──────────────────┬────────────────┘      └──────────────┘
                      │
          ┌───────────▼───────────┐
          │  Ollama (local GPU)   │
          │  or Remote inference  │
          └───────────────────────┘
```

---

## Roadmap

- [ ] Bootstrap installer script (single `curl | bash` command)
- [ ] Bootable ISO installer for fresh Ubuntu 24.04 installs
- [ ] Web-based management UI for container control and config
- [ ] Built-in documentation site (self-hosted, runs in the stack)
- [ ] MCP server integration for AI tool access
- [ ] Multi-node support (dedicated inference server setup)
- [ ] Community module system for extending the stack

---

## Philosophy

**Local first.** Every service runs on your hardware. Your data does not leave your machine unless you explicitly configure it to.

**Opinionated but extensible.** Tronexus makes choices so you do not have to spend weeks integrating disparate tools. Every choice is documented and reversible.

**Minimal hardware floor.** Designed to run on a single mid-range machine with a consumer GPU. Cloud-grade hardware is not required.

**Production-grade from day one.** TLS, authentication, monitoring, and automated container recovery are included — not afterthoughts.

**Security is not optional.** Tronexus ships with a hardened Ubuntu 24.04 base — fail2ban, UFW, SSH hardening, automatic security updates, and audited service configuration are part of the default install. The same security standards applied to professional infrastructure are applied here.

---

## Contributing

Tronexus is in early development. The best way to contribute right now is to try it, break it, and open an issue.

- [Open an issue](https://github.com/Tronexus/tronexus-stack/issues)
- [Start a discussion](https://github.com/Tronexus/tronexus-stack/discussions)

---

## License

MIT — use it, fork it, build on it.

---

> *"The computer is the most creative tool we have ever built. It is time we ran our own."*
>
> — tronexus.dev
