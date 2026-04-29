#!/bin/bash
# weekly-radar.sh - Run GitHub radar weekly
export PATH="$HOME/.openclaw/bin:$PATH:$HOME/.local/bin"
github-radar.py --days 7 --save
