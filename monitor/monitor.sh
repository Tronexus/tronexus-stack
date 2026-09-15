#!/bin/bash
# =============================================================================
# TRONEXUS STACK — Server Monitor
# =============================================================================
# Runs daily via cron. Checks container health, disk, security, backups,
# and API key expiry. Sends a Telegram alert with AI-generated summary.
#
# Setup: add to crontab with: crontab -e
# 0 18 * * * /opt/tronexus/monitor/monitor.sh >> /opt/tronexus/monitor/monitor.log 2>&1
# =============================================================================

set -a
source /opt/tronexus/.env
set +a

TELEGRAM_URL="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
DATE=$(date '+%d %b %Y %H:%M')
FINDINGS=""
ALL_OK=true

# ── Docker container health ──────────────────────────────────────────────────
UNHEALTHY=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" 2>/dev/null)
RESTARTING=$(docker ps --filter "status=restarting" --format "{{.Names}}" 2>/dev/null)

if [ -n "$UNHEALTHY" ]; then
    for container in $UNHEALTHY; do
        docker restart "$container" > /dev/null 2>&1
        FINDINGS="${FINDINGS}AUTO-FIXED: Restarted unhealthy container: ${container}\n"
    done
    ALL_OK=false
fi

if [ -n "$RESTARTING" ]; then
    FINDINGS="${FINDINGS}CONTAINER: ${RESTARTING} is in restart loop\n"
    ALL_OK=false
fi

# ── Container logs — recurring errors in last 24h ────────────────────────────
# Count DISTINCT error signatures, not raw lines: one multi-line stack trace
# would otherwise be counted many times (a single Node "fetch failed" trace is
# 5-15 matching lines). Timestamps, numbers and hex are normalised out so
# repeats of the same error collapse into one signature. Alert when any single
# signature recurs more than ERROR_SIGNATURE_THRESHOLD times, and name it so the
# report is actionable rather than just a line count.
ERROR_SIGNATURE_THRESHOLD="${ERROR_SIGNATURE_THRESHOLD:-5}"
for container in $(docker ps --format "{{.Names}}"); do
    TOP=$(docker logs --since 24h "$container" 2>&1 \
        | grep -iE "error|fatal|critical" \
        | grep -viE "deprecat|warn|info|health|handshake error|no certificate available" \
        | sed -E 's/^[0-9]{4}-[0-9-]*T[0-9:.]+Z?[[:space:]]*//; s/0x[0-9a-fA-F]+/0xHEX/g; s/[0-9]+/N/g; s/[[:space:]]+/ /g; s/^ //; s/ $//' \
        | sort | uniq -c | sort -rn | head -1)
    COUNT=$(echo "$TOP" | awk '{print $1}'); COUNT=${COUNT:-0}
    if [ "$COUNT" -gt "$ERROR_SIGNATURE_THRESHOLD" ]; then
        SIG=$(echo "$TOP" | sed -E 's/^[[:space:]]*[0-9]+[[:space:]]*//' | cut -c1-120)
        FINDINGS="${FINDINGS}LOGS: ${container}: ${COUNT}x \"${SIG}\" in last 24h\n"
        ALL_OK=false
    fi
done

# ── TLS handshake scan volume (attack indicator) ─────────────────────────────
# A public-facing 443 gets constant background scanning (incomplete-TLS probes,
# bogus SNI). Caddy logs these as "handshake error". That noise is excluded from
# the error counter above; here we alert only on an unusual SPIKE, reported as
# SECURITY rather than a log error. Calibrate HANDSHAKE_SCAN_THRESHOLD in .env to
# roughly 2x your server's normal daily count. Check your baseline with:
#   docker logs --since 24h tronexus-caddy 2>&1 | grep -c "handshake error"
HANDSHAKE_SCAN_THRESHOLD="${HANDSHAKE_SCAN_THRESHOLD:-10000}"
HANDSHAKE_SCANS=$(docker logs --since 24h tronexus-caddy 2>&1 | grep -ic "handshake error")
if [ "$HANDSHAKE_SCANS" -gt "$HANDSHAKE_SCAN_THRESHOLD" ]; then
    FINDINGS="${FINDINGS}SECURITY: Unusually high TLS scan volume - ${HANDSHAKE_SCANS} handshake probes in 24h (threshold ${HANDSHAKE_SCAN_THRESHOLD})\n"
    ALL_OK=false
fi

# ── Disk usage ───────────────────────────────────────────────────────────────
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
    FINDINGS="${FINDINGS}DISK: Usage critical at ${DISK_USAGE}%\n"
    ALL_OK=false
fi

# ── fail2ban ─────────────────────────────────────────────────────────────────
BANS=$(sudo zgrep "Ban" /var/log/fail2ban.log 2>/dev/null | grep -c "$(date +%Y-%m-%d)")
if [ -n "$BANS" ] && [ "$BANS" -gt 0 ]; then
    FINDINGS="${FINDINGS}SECURITY: fail2ban SSH bans today: ${BANS}\n"
fi

# ── Backup check ─────────────────────────────────────────────────────────────
if [ -f /opt/tronexus/backups/backup.log ]; then
    if ! tail -1 /opt/tronexus/backups/backup.log | grep -q "completed"; then
        FINDINGS="${FINDINGS}BACKUP: Last backup may have failed\n"
        ALL_OK=false
    fi
fi

# ── Auth API key expiry ──────────────────────────────────────────────────────
EXPIRING_KEYS=$(docker exec tronexus-postgres psql -U "$POSTGRES_USER" -d auth -t -c "
    SELECT ak.name || ' (app: ' || a.name || ', expires: ' || TO_CHAR(ak.expires_at, 'DD Mon YYYY') || ')'
    FROM api_keys ak
    JOIN apps a ON a.id = ak.app_id
    WHERE ak.revoked = false
      AND ak.expires_at BETWEEN now() AND now() + INTERVAL '14 days';
" 2>/dev/null | sed '/^\s*$/d')

if [ -n "$EXPIRING_KEYS" ]; then
    while IFS= read -r key_line; do
        FINDINGS="${FINDINGS}AUTH: API key expiring soon: ${key_line}\n"
    done <<< "$EXPIRING_KEYS"
    ALL_OK=false
fi

# ── apt security updates ─────────────────────────────────────────────────────
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
if [ "$SECURITY_UPDATES" -gt 0 ]; then
    FINDINGS="${FINDINGS}UPDATES: ${SECURITY_UPDATES} security updates pending\n"
fi

# ── Remote inference server health ───────────────────────────────────────────
if [ -n "$INFERENCE_HOST" ]; then
    INFERENCE_CHECK=$(curl -s --connect-timeout 5 "http://${INFERENCE_HOST}:11434/api/tags" | \
        python3 -c "import json,sys; data=json.load(sys.stdin); print('ok')" 2>/dev/null)
    if [ "$INFERENCE_CHECK" != "ok" ]; then
        FINDINGS="${FINDINGS}INFERENCE: Remote Ollama at ${INFERENCE_HOST} unreachable\n"
        ALL_OK=false
    fi
fi

# ── AI summary via Ollama ────────────────────────────────────────────────────
OLLAMA_URL="http://localhost:11434"
if [ -n "$INFERENCE_HOST" ]; then
    OLLAMA_URL="http://${INFERENCE_HOST}:11434"
fi

if [ "$ALL_OK" = false ] || [ -n "$FINDINGS" ]; then
    PROMPT="Summarise the following server monitoring findings in plain text. No markdown. No bullet symbols. Maximum 150 words.
Line 1 must be exactly one of: STATUS: STABLE or STATUS: MONITOR or STATUS: ATTENTION REQUIRED.
Only report what is listed. Do not invent or infer additional issues.

FINDINGS:
$(echo -e "$FINDINGS")

SYSTEM INFO:
- Disk: ${DISK_USAGE}% used
- Date: ${DATE}"

    AI_RESPONSE=$(curl -s "${OLLAMA_URL}/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"mistral:7b-instruct-q4_K_M\", \"prompt\": $(echo "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'), \"stream\": false}" | \
        python3 -c "import json,sys; data=json.load(sys.stdin); print(data['response'])" 2>/dev/null)
    AI_RESPONSE=$(echo "$AI_RESPONSE" | head -c 3500)
    REPORT="TRONEXUS SERVER REPORT — ${DATE}

${AI_RESPONSE}"
else
    REPORT="TRONEXUS SERVER REPORT — ${DATE}

STATUS: STABLE

All systems operational. No issues detected.
Disk: ${DISK_USAGE}% used."
fi

# ── Send to Telegram ──────────────────────────────────────────────────────────
curl -s -X POST "$TELEGRAM_URL" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    --data-urlencode "text=${REPORT}" \
    -d parse_mode="HTML" > /dev/null
