#!/bin/bash
# Agent-Specific File Watcher
AGENT="${1:-coder}"
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
WATCH_DIR="$WORKSPACE/subagents/$AGENT"

echo "👁️  Watching: $AGENT"
while true; do
  sleep 5
  find "$WATCH_DIR" -type f -mmin -0.1 2>/dev/null | while read f; do
    echo "📝 Changed: $(basename "$f")"
    "$WORKSPACE/subagents/reviewer/review.sh" "$f"
  done
done