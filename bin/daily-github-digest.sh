#!/bin/bash
# daily-github-digest.sh - Run digest and send to Telegram
cd "$HOME"
export PATH="$HOME/.openclaw/bin:$PATH:$HOME/.local/bin"

# Load env vars from shell
source "$HOME/.zshrc" 2>/dev/null || source "$HOME/.bashrc" 2>/dev/null

# Generate digest
DIGEST=$(github-digest.py --since 24 2>/dev/null)

# Check if there's anything interesting
if echo "$DIGEST" | grep -q "🚀\|🔹"; then
    # Send to Telegram
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID:-791865934}" \
        -d "text=${DIGEST}" \
        -d "parse_mode=Markdown" \
        -d "disable_web_page_preview=true" \
        > /dev/null 2>&1
    
    echo "Sent digest to Telegram"
else
    echo "No activity today. Skipping."
fi
