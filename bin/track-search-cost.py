#!/usr/bin/env python3
"""
Track web search usage and compute estimated costs.
Usage:
  track-search-cost.py web_search "query here" [estimated_tokens]
  track-search-cost.py x_search "query here" [estimated_tokens]
  track-search-cost.py web_fetch "https://url" [estimated_tokens]
  track-search-cost.py summary                    # Show totals
"""
import json
import sys
import os
from datetime import datetime, timezone

LOG_FILE = os.path.expanduser("~/.openclaw/web-search-usage.log")

# Pricing (USD) - update as providers change
PRICING = {
    "web_search": {
        "search_cost": 0.075,           # per 1000 searches (Google Search grounding)
        "input_per_1m": 0.075,          # per 1M input tokens (Gemini 2.0 Flash)
        "output_per_1m": 0.30,          # per 1M output tokens
        "avg_input_tokens": 50,         # query tokens
        "avg_output_tokens": 2000,     # search results + synthesis
    },
    "x_search": {
        "search_cost": 0.10,            # per 1000 queries (xAI/Grok estimate)
        "input_per_1m": 0.50,            # per 1M input tokens (Grok estimate)
        "output_per_1m": 2.00,           # per 1M output tokens
        "avg_input_tokens": 50,
        "avg_output_tokens": 1500,
    },
    "web_fetch": {
        "cost": 0.00,
        "avg_tokens": 0,
    }
}

def estimate_tokens(tool, query):
    """Rough token estimation. ~4 chars per token for English text."""
    if tool == "web_fetch":
        return 0
    pricing = PRICING.get(tool, PRICING["web_search"])
    query_tokens = max(len(query) // 4, 10)
    return pricing["avg_input_tokens"] + pricing["avg_output_tokens"]

def compute_cost(tool, tokens):
    """Compute estimated cost in USD."""
    if tool == "web_fetch":
        return 0.0
    pricing = PRICING.get(tool, PRICING["web_search"])
    search_cost = pricing.get("search_cost", 0) / 1000  # per query
    input_cost = (pricing.get("avg_input_tokens", 50) / 1_000_000) * pricing["input_per_1m"]
    output_cost = (pricing.get("avg_output_tokens", 2000) / 1_000_000) * pricing["output_per_1m"]
    return search_cost + input_cost + output_cost

def log_usage(tool, query, tokens=None):
    """Log a search usage entry."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    if tokens is None:
        tokens = estimate_tokens(tool, query)
    
    cost = compute_cost(tool, tokens)
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "query": query,
        "tokens": tokens,
        "cost_usd": round(cost, 6)
    }
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"Logged: {tool} | {query[:50]}{'...' if len(query) > 50 else ''} | ~{tokens} tokens | ${cost:.6f}")
    return cost

def show_summary():
    """Show usage summary."""
    if not os.path.exists(LOG_FILE):
        print("No usage logged yet.")
        return
    
    total_cost = 0.0
    total_searches = 0
    total_tokens = 0
    tool_counts = {}
    daily_costs = {}
    
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                tool = entry["tool"]
                cost = entry.get("cost_usd", 0)
                tokens = entry.get("tokens", 0)
                date = entry["timestamp"][:10]
                
                total_cost += cost
                total_tokens += tokens
                total_searches += 1
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
                daily_costs[date] = daily_costs.get(date, 0) + cost
            except (json.JSONDecodeError, KeyError):
                continue
    
    print("\n" + "=" * 50)
    print("WEB SEARCH USAGE SUMMARY")
    print("=" * 50)
    print(f"Total searches:     {total_searches}")
    print(f"Total tokens:       {total_tokens:,}")
    print(f"Total cost (USD):   ${total_cost:.4f}")
    print(f"Total cost (INR):   ₹{total_cost * 83:.2f} (approx)")
    print("\nBy tool:")
    for tool, count in sorted(tool_counts.items()):
        print(f"  {tool:15s} {count:4d} searches")
    print("\nDaily costs:")
    for date in sorted(daily_costs.keys(), reverse=True)[:7]:
        print(f"  {date}  ${daily_costs[date]:.4f}")
    print("=" * 50)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "summary":
        show_summary()
    elif command in ("web_search", "x_search", "web_fetch"):
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} {command} <query_or_url> [tokens]")
            sys.exit(1)
        query = sys.argv[2]
        tokens = int(sys.argv[3]) if len(sys.argv) > 3 else None
        log_usage(command, query, tokens)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
