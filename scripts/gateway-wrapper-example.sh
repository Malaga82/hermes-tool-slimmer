#!/bin/bash
# Persistent startup hook for Command Code proxy
# Location: /opt/data/scripts/gateway-wrapper.sh (IN THE VOLUME — survives updates)
#
# This script starts the cmdcode proxy, then hands off to the real Hermes entrypoint.

set -e

HERMES_HOME="${HERMES_HOME:-/opt/data}"
ENTRYPOINT="/opt/hermes/docker/entrypoint.sh"

# --- Start Command Code proxy (Go fork Malaga) ---
CC_PORT="${HERMES_CMDCODE_PORT:-8421}"
CC_BINARY="$HERMES_HOME/cc-proxy-go-malaga/cc-proxy"
CC_ENV="$HERMES_HOME/cc-proxy-go-malaga/.env"

if [ -f "$CC_BINARY" ]; then
    # Kill stale instance if any
    if [ -f /tmp/cc-proxy.pid ]; then
        kill "$(cat /tmp/cc-proxy.pid)" 2>/dev/null || true
    fi
    pkill -9 -f 'cc-proxy' 2>/dev/null || true

    echo "Starting Command Code Go proxy on 127.0.0.1:${CC_PORT} (background)"
    cd "$HERMES_HOME/cc-proxy-go-malaga"
    PORT="$CC_PORT" \
    COMMAND_CODE_TOKEN="$(grep COMMAND_CODE_TOKEN "$CC_ENV" | cut -d= -f2-)" \
    COMMAND_CODE_VERSION="$(grep COMMAND_CODE_VERSION "$CC_ENV" | cut -d= -f2-)" \
    nohup "$CC_BINARY" > /tmp/cc-proxy.log 2>&1 &
    echo $! > /tmp/cc-proxy.pid
    sleep 2

    if curl -sf "http://127.0.0.1:${CC_PORT}/healthz" > /dev/null 2>&1; then
        echo "Command Code Go proxy ready"
    else
        echo "WARNING: Command Code Go proxy not responding (may need more time)"
    fi
else
    echo "Command Code Go proxy binary not found at $CC_BINARY — skipping"
fi

# --- Check tool-slimmer core patch status ---
PATCH_CHECK="/opt/data/scripts/check-tool-slimmer-patch.py"
if [ -f "$PATCH_CHECK" ]; then
    PATCH_OUTPUT=$(/opt/hermes/.venv/bin/python3 "$PATCH_CHECK" 2>&1) || {
        echo "$PATCH_OUTPUT"
        echo "⚠️  tool-slimmer patch NOT applied — sending Discord notification"
        # Send Discord notification via webhook
        DISCORD_WEBHOOK_URL="${DISCORD_PATCH_WEBHOOK:-}"
        if [ -n "$DISCORD_WEBHOOK_URL" ]; then
            MESSAGE="⚠️ **tool-slimmer patch non applicata** dopo l'ultimo avvio.\nIl tool-slimmer è installato ma la core patch manca — nessun risparmio token.\n\nPer fixare:\n\`\`\`bash\ncd /opt/hermes && patch -p1 -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch\n\`\`\`\nPoi riavvia il gateway."
            curl -sf -X POST "$DISCORD_WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{\"content\": \"$MESSAGE\"}" > /dev/null 2>&1 || true
        else
            echo "   (no DISCORD_PATCH_WEBHOOK set — skipping Discord notification)"
            echo "   Set DISCORD_PATCH_WEBHOOK in .env to enable notifications"
        fi
    }
fi

# --- Hand off to the real entrypoint ---
exec "$ENTRYPOINT" "$@"
