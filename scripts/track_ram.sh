#!/bin/bash
# Hourly location tracker for RamEsh
# Sends reminder to share location for speed/ETA calculation

CHAT_ID="791865934"
TIME=$(date '+%H:%M IST')

curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
  -d "chat_id=$CHAT_ID" \
  -d "text=🚗 Hourly check-in ($TIME)\n\nShare your location for:\n📍 Current position\n🚗 Speed update\n⏱️ ETA to Ashwins Perambalur\n\nJust tap 📎 → Location" 2>/dev/null
