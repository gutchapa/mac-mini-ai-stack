#!/bin/bash
# memory-flush.sh - Auto-save session context to daily memory file
# Usage: ./memory-flush.sh ["optional context message"]

WORKSPACE="/home/dell/.openclaw/workspace"
MEMORY_DIR="$WORKSPACE/memory"
DATE=$(date '+%Y-%m-%d')
TIME=$(date '+%H:%M')
TIMESTAMP=$(date '+%s')
MEMORY_FILE="$MEMORY_DIR/$DATE.md"

# Ensure memory directory exists
mkdir -p "$MEMORY_DIR"

# Create header if file doesn't exist
if [ ! -f "$MEMORY_FILE" ]; then
    echo "# Session Log - $DATE" > "$MEMORY_FILE"
    echo "" >> "$MEMORY_FILE"
    echo "Auto-generated session context." >> "$MEMORY_FILE"
    echo "" >> "$MEMORY_FILE"
fi

# Append new entry
echo "" >> "$MEMORY_FILE"
echo "## $TIME UTC" >> "$MEMORY_FILE"
echo "" >> "$MEMORY_FILE"

# If context provided via argument, use it
if [ -n "$1" ]; then
    echo "$1" >> "$MEMORY_FILE"
else
    # Otherwise, detect recent activity
    echo "### Recent Activity Detected:" >> "$MEMORY_FILE"
    echo "" >> "$MEMORY_FILE"
    
    # Check for route cache
    if [ -f "$WORKSPACE/driving-assistant/.route_cache.json" ]; then
        echo "- 🗺️ Route cache updated" >> "$MEMORY_FILE"
    fi
    
    # Check for agent output
    RECENT_OUTPUT=$(find "$WORKSPACE/agent-output" -type d -mtime -0.01 2>/dev/null | head -3)
    if [ -n "$RECENT_OUTPUT" ]; then
        echo "- 🤖 Agent tasks completed" >> "$MEMORY_FILE"
    fi
    
    # Check git status
    cd "$WORKSPACE" && git diff --quiet 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "- 💻 Uncommitted code changes" >> "$MEMORY_FILE"
    fi
    
    # Check for violations
    if [ -f "$MEMORY_DIR/soul-violations.md" ]; then
        RECENT_VIOLATIONS=$(tail -20 "$MEMORY_DIR/soul-violations.md" 2>/dev/null | grep -c "Violation")
        if [ "$RECENT_VIOLATIONS" -gt 0 ]; then
            echo "- ⚠️ $RECENT_VIOLATIONS SOUL-EL violations logged" >> "$MEMORY_FILE"
        fi
    fi
fi

echo "" >> "$MEMORY_FILE"
echo "---" >> "$MEMORY_FILE"

echo "✅ Flushed to $MEMORY_FILE"
