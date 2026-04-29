#!/bin/bash
# track-search-cost.sh - Simple web search usage tracker
# Usage: track-search-cost.sh <tool> <query_or_url> [tokens]

LOG_FILE="$HOME/.openclaw/web-search-usage.log"
mkdir -p "$(dirname "$LOG_FILE")"

TOOL="$1"
QUERY="$2"
TOKENS="${3:-0}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Pricing (approximate, update as needed)
# Gemini web_search grounding: ~$0.075 per 1000 searches (not token-based)
# Gemini 2.0 Flash: $0.075 / 1M input tokens, $0.30 / 1M output tokens
# xAI Grok: varies by model

case "$TOOL" in
  web_search)
    COST_PER_1K_SEARCH=0.075
    # Estimate tokens: query ~50 tokens + results ~2000 tokens avg
    EST_TOKENS=${TOKENS:-2050}
    COST=$(echo "scale=6; $EST_TOKENS * 0.000000075 + 0.075" | bc 2>/dev/null || echo "0.000")
    ;;
  x_search)
    COST_PER_1K_SEARCH=0.10
    EST_TOKENS=${TOKENS:-1500}
    COST=$(echo "scale=6; $EST_TOKENS * 0.0000001 + 0.10" | bc 2>/dev/null || echo "0.000")
    ;;
  web_fetch)
    COST="0.000"
    EST_TOKENS=${TOKENS:-0}
    ;;
  *)
    COST="0.000"
    EST_TOKENS=${TOKENS:-0}
    ;;
esac

# Append to log
cat >> "$LOG_FILE" << EOF
{"timestamp":"$TIMESTAMP","tool":"$TOOL","query":"$QUERY","tokens":$EST_TOKENS,"cost_usd":$COST}
EOF

echo "Logged: $TOOL | ${QUERY:0:50}... | ~$EST_TOKENS tokens | \$$COST"
