#!/bin/bash
# =============================================================================
# TRONEXUS STACK — Installer
# =============================================================================
# Installs and configures the full Tronexus stack on Ubuntu 24.04 LTS.
# Run as root or with sudo.
#
# Usage:
#   curl -fsSL https://tronexus.dev/install.sh | sudo bash
#   — or —
#   sudo bash install.sh
# =============================================================================

set -e

TRONEXUS_DIR="/opt/tronexus"
REPO_URL="https://github.com/Tronexus/tronexus-stack.git"
LOG_FILE="/var/log/tronexus-install.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()   { echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }
info()  { echo -e "${CYAN}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
header(){ echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}\n"; }

# =============================================================================
# PREFLIGHT
# =============================================================================
header "Tronexus Stack Installer"

if [ "$EUID" -ne 0 ]; then
    error "Please run as root or with sudo."
fi

OS=$(lsb_release -si 2>/dev/null || echo "unknown")
VER=$(lsb_release -sr 2>/dev/null || echo "0")

if [ "$OS" != "Ubuntu" ] || [ "$(echo "$VER < 24.0" | bc)" -eq 1 ]; then
    error "Tronexus requires Ubuntu 24.04 LTS. Detected: ${OS} ${VER}"
fi

log "Ubuntu 24.04 LTS confirmed"

RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [ "$RAM_GB" -lt 12 ]; then
    warn "Detected ${RAM_GB}GB RAM. Tronexus recommends at least 15GB."
fi

DISK_FREE=$(df / | awk 'NR==2 {print int($4/1024/1024)}')
if [ "$DISK_FREE" -lt 50 ]; then
    warn "Only ${DISK_FREE}GB free disk space. Tronexus recommends at least 100GB free."
fi

# =============================================================================
# SYSTEM UPDATE
# =============================================================================
header "System Update"
info "Updating package lists..."
apt-get update -qq | tee -a "$LOG_FILE"
apt-get upgrade -y -qq | tee -a "$LOG_FILE"
apt-get install -y -qq curl git ufw fail2ban unattended-upgrades \
    apt-listchanges python3 python3-pip bc | tee -a "$LOG_FILE"
log "System packages updated"

# =============================================================================
# UBUNTU HARDENING
# =============================================================================
header "Ubuntu Security Hardening"

# SSH hardening
info "Hardening SSH configuration..."
SSH_CONFIG="/etc/ssh/sshd_config"
cp "$SSH_CONFIG" "${SSH_CONFIG}.bak.$(date +%Y%m%d)"

declare -A SSH_SETTINGS=(
    ["PermitRootLogin"]="no"
    ["PasswordAuthentication"]="no"
    ["PubkeyAuthentication"]="yes"
    ["X11Forwarding"]="no"
    ["MaxAuthTries"]="3"
    ["LoginGraceTime"]="20"
    ["AllowTcpForwarding"]="no"
    ["ClientAliveInterval"]="300"
    ["ClientAliveCountMax"]="2"
)

for key in "${!SSH_SETTINGS[@]}"; do
    value="${SSH_SETTINGS[$key]}"
    if grep -q "^${key}" "$SSH_CONFIG"; then
        sed -i "s/^${key}.*/${key} ${value}/" "$SSH_CONFIG"
    else
        echo "${key} ${value}" >> "$SSH_CONFIG"
    fi
done

systemctl reload sshd
log "SSH hardened"

# UFW firewall
info "Configuring UFW firewall..."
ufw --force reset > /dev/null
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null
ufw allow ssh > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw --force enable > /dev/null
log "UFW firewall enabled (SSH, HTTP, HTTPS only)"

# fail2ban
info "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'F2B'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
maxretry = 3
bantime  = 86400
F2B
systemctl enable fail2ban > /dev/null
systemctl restart fail2ban > /dev/null
log "fail2ban configured"

# Automatic security updates
info "Enabling automatic security updates..."
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
APT
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UU'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
UU
log "Automatic security updates enabled"

# sysctl hardening
info "Applying sysctl hardening..."
cat > /etc/sysctl.d/99-tronexus-hardening.conf << 'SYSCTL'
# Network hardening
net.ipv4.ip_forward = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.tcp_syncookies = 1
net.ipv6.conf.all.accept_redirects = 0

# Memory hardening
kernel.randomize_va_space = 2
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
SYSCTL
sysctl --system > /dev/null
log "sysctl hardening applied"

log "Ubuntu hardening complete"

# =============================================================================
# DOCKER
# =============================================================================
header "Docker Installation"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log "Docker already installed: ${DOCKER_VERSION}"
else
    info "Installing Docker..."
    curl -fsSL https://get.docker.com | sh >> "$LOG_FILE" 2>&1
    systemctl enable docker > /dev/null
    systemctl start docker > /dev/null
    log "Docker installed"
fi

# Add current user to docker group if not root
REAL_USER="${SUDO_USER:-$USER}"
if [ "$REAL_USER" != "root" ]; then
    usermod -aG docker "$REAL_USER"
    log "Added ${REAL_USER} to docker group"
fi

# =============================================================================
# CLONE REPOSITORY
# =============================================================================
header "Tronexus Stack Setup"

if [ -d "$TRONEXUS_DIR/.git" ]; then
    info "Tronexus directory exists, pulling latest..."
    git -C "$TRONEXUS_DIR" pull >> "$LOG_FILE" 2>&1
else
    info "Cloning Tronexus stack..."
    git clone "$REPO_URL" "$TRONEXUS_DIR" >> "$LOG_FILE" 2>&1
fi

log "Tronexus stack cloned to ${TRONEXUS_DIR}"

# =============================================================================
# CONFIGURATION WIZARD
# =============================================================================
header "Configuration Wizard"

echo -e "Let's configure your Tronexus stack."
echo -e "Press ${BOLD}Enter${NC} to accept defaults where shown.\n"

prompt() {
    local var=$1
    local label=$2
    local default=$3
    local secret=$4

    if [ -n "$default" ]; then
        echo -ne "${CYAN}${label}${NC} [${default}]: "
    else
        echo -ne "${CYAN}${label}${NC}: "
    fi

    if [ "$secret" = "true" ]; then
        read -rs value
        echo
    else
        read -r value
    fi

    if [ -z "$value" ] && [ -n "$default" ]; then
        value="$default"
    fi
    eval "$var='$value'"
}

generate_secret() {
    openssl rand -hex 32
}

generate_short_secret() {
    openssl rand -hex 16
}

# General
prompt TRONEXUS_DOMAIN "Your domain (e.g. example.com)" "" false
prompt TZ "Timezone" "Europe/Amsterdam" false

# Postgres
prompt POSTGRES_USER "Postgres username" "tronexus" false
prompt POSTGRES_PASSWORD "Postgres password (leave blank to generate)" "" true
if [ -z "$POSTGRES_PASSWORD" ]; then
    POSTGRES_PASSWORD=$(generate_secret)
    info "Generated Postgres password"
fi
POSTGRES_DB="tronexus"

# Auth API
prompt AUTH_GOOGLE_CLIENT_ID "Google OAuth Client ID" "" false
prompt AUTH_GOOGLE_CLIENT_SECRET "Google OAuth Client Secret" "" true
AUTH_JWT_SECRET=$(generate_secret)
info "Generated JWT secret"

# LiteLLM
LITELLM_MASTER_KEY=$(generate_short_secret)
info "Generated LiteLLM master key"

# Open WebUI
WEBUI_SECRET_KEY=$(generate_secret)
info "Generated WebUI secret key"

# n8n
N8N_ENCRYPTION_KEY=$(generate_short_secret)
info "Generated n8n encryption key"

# pgAdmin
prompt PGADMIN_DEFAULT_EMAIL "pgAdmin admin email" "admin@${TRONEXUS_DOMAIN}" false
prompt PGADMIN_DEFAULT_PASSWORD "pgAdmin admin password (leave blank to generate)" "" true
if [ -z "$PGADMIN_DEFAULT_PASSWORD" ]; then
    PGADMIN_DEFAULT_PASSWORD=$(generate_short_secret)
    info "Generated pgAdmin password"
fi

# Monitoring
echo ""
info "Monitoring (optional — press Enter to skip)"
prompt TELEGRAM_BOT_TOKEN "Telegram bot token" "" false
prompt TELEGRAM_CHAT_ID "Telegram chat ID" "" false

# Remote inference
echo ""
prompt INFERENCE_HOST "Remote inference server IP (leave blank if using local GPU)" "" false

# Auth API base URL
AUTH_API_BASE_URL="https://auth-api.${TRONEXUS_DOMAIN}"

# =============================================================================
# WRITE .env
# =============================================================================
header "Writing Configuration"

cat > "${TRONEXUS_DIR}/.env" << ENV
# Generated by Tronexus installer on $(date)

# GENERAL
TRONEXUS_DOMAIN=${TRONEXUS_DOMAIN}
TZ=${TZ}

# POSTGRES
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}

# AUTH API
AUTH_GOOGLE_CLIENT_ID=${AUTH_GOOGLE_CLIENT_ID}
AUTH_GOOGLE_CLIENT_SECRET=${AUTH_GOOGLE_CLIENT_SECRET}
AUTH_JWT_SECRET=${AUTH_JWT_SECRET}
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=30
AUTH_API_BASE_URL=${AUTH_API_BASE_URL}
AUTH_DB_NAME=auth
AUTH_APP_ID=
AUTH_RATE_LIMIT_WINDOW=60
AUTH_RATE_LIMIT_MAX=20
AUTH_LOCKOUT_ATTEMPTS=10
AUTH_LOCKOUT_SECONDS=900

# REDIS
REDIS_HOST=tronexus-redis
REDIS_PORT=6379

# LITELLM
LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}

# OPEN WEBUI
WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}

# N8N
N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
N8N_BASIC_AUTH_ACTIVE=false
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=

# PGADMIN
PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL}
PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD}

# MONITORING
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
INFERENCE_HOST=${INFERENCE_HOST}
ENV

chmod 600 "${TRONEXUS_DIR}/.env"
log ".env written and secured"

# =============================================================================
# CRON — MONITORING
# =============================================================================
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    chmod +x "${TRONEXUS_DIR}/monitor/monitor.sh"
    mkdir -p "${TRONEXUS_DIR}/backups"
    CRON_LINE="0 18 * * * ${TRONEXUS_DIR}/monitor/monitor.sh >> ${TRONEXUS_DIR}/monitor/monitor.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "monitor.sh"; echo "$CRON_LINE") | crontab -
    log "Monitoring cron job installed (daily at 18:00)"
fi

# =============================================================================
# START STACK
# =============================================================================
header "Starting Tronexus Stack"

cd "$TRONEXUS_DIR"
docker compose pull >> "$LOG_FILE" 2>&1
docker compose build >> "$LOG_FILE" 2>&1
docker compose up -d >> "$LOG_FILE" 2>&1

# Wait for stack to settle
info "Waiting for services to start..."
sleep 15

# Check container status
RUNNING=$(docker compose ps --status running --format "{{.Name}}" | wc -l)
TOTAL=$(docker compose ps --format "{{.Name}}" | wc -l)
log "${RUNNING}/${TOTAL} containers running"

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================
header "Installation Complete"

echo -e "${GREEN}${BOLD}Tronexus stack is running.${NC}\n"
echo -e "Your services are available at:\n"
echo -e "  ${CYAN}AI Interface:${NC}    https://${TRONEXUS_DOMAIN}"
echo -e "  ${CYAN}Auth API:${NC}        https://auth-api.${TRONEXUS_DOMAIN}/health"
echo -e "  ${CYAN}n8n Automation:${NC}  https://n8n.${TRONEXUS_DOMAIN}"
echo -e "  ${CYAN}pgAdmin:${NC}         https://pgadmin.${TRONEXUS_DOMAIN}"
echo ""
echo -e "${YELLOW}${BOLD}Next steps:${NC}"
echo -e "  1. Ensure DNS records point to this server for all subdomains"
echo -e "  2. Run the auth bootstrap: cd ${TRONEXUS_DIR} && bash scripts/bootstrap-auth.sh"
echo -e "  3. Pull your first AI model: docker exec tronexus-ollama ollama pull mistral"
echo ""
echo -e "${YELLOW}Credentials and secrets are stored in:${NC} ${TRONEXUS_DIR}/.env"
echo -e "${YELLOW}Installation log:${NC} ${LOG_FILE}"
echo ""
