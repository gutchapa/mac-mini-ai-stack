#!/bin/bash
# Multi-Agent Watcher System
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"

echo "🤖 Multi-Agent File Watcher"
echo "=========================="

for agent in coder researcher planner executor reviewer; do
  if [ -d "$WORKSPACE/subagents/$agent" ]; then
    echo "👁️  Starting: $agent"
    "$WORKSPACE/agent-watch.sh" "$agent" &
  fi
done

echo ""
echo "✅ All watchers started"
echo "Press Ctrl+C to stop"
wait