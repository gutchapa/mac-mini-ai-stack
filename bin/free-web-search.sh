#!/bin/bash
# free-web-search.sh - Zero-cost web search using DuckDuckGo + local Ollama
# Usage: free-web-search.sh "your search query"

set -e

QUERY="$1"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:e4b-q4}"

if [ -z "$QUERY" ]; then
    echo "Usage: $0 \"your search query\""
    exit 1
fi

echo "🔍 Searching DuckDuckGo for: $QUERY"

# DuckDuckGo HTML search (no API key needed)
# Use their lite version for cleaner HTML
ENCODED_QUERY=$(echo "$QUERY" | sed 's/ /+/g')
SEARCH_URL="https://duckduckgo.com/html/?q=${ENCODED_QUERY}"

# Fetch results (with user agent to avoid blocks)
RESULTS=$(curl -s -L \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
    "$SEARCH_URL" 2>/dev/null | \
    grep -oP '(?<=<a class="result__a" href=")[^"]+' | \
    head -5)

if [ -z "$RESULTS" ]; then
    echo "❌ No results found or DuckDuckGo blocked the request"
    echo "Trying alternative approach..."
    
    # Fallback: Try textise dot iitty approach
    RESULTS=$(curl -s "https://html.duckduckgo.com/html/?q=${ENCODED_QUERY}" \
        -H "User-Agent: Mozilla/5.0" 2>/dev/null | \
        grep -oP '(?<=<a rel="nofollow" class="result__a" href=")[^"]+' | \
        head -5)
fi

if [ -z "$RESULTS" ]; then
    echo "❌ Still no results. DuckDuckGo may be blocking automated requests."
    exit 1
fi

echo ""
echo "📄 Found URLs, fetching content..."

# Fetch content from top 3 results
CONTENT=""
count=0
for url in $RESULTS; do
    count=$((count + 1))
    if [ $count -gt 3 ]; then
        break
    fi
    
    echo "  → Fetching: $url"
    
    # Fetch and extract text (simple HTML to text conversion)
    page_content=$(curl -s -L \
        -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
        --max-time 10 \
        "$url" 2>/dev/null | \
        sed 's/<[^>]*>//g' | \
        tr -s ' \n' | \
        head -c 3000)
    
    if [ -n "$page_content" ]; then
        CONTENT="${CONTENT}\n\n--- SOURCE ${count}: ${url} ---\n${page_content}"
    fi
done

if [ -z "$CONTENT" ]; then
    echo "❌ Could not fetch any content from results"
    exit 1
fi

echo ""
echo "🤖 Sending to local Ollama ($OLLAMA_MODEL) for synthesis..."

# Create prompt for Ollama
PROMPT="Based on the following web search results about \"$QUERY\", provide a comprehensive answer. Cite sources where relevant.\n\n${CONTENT}\n\nAnswer:"

# Run through Ollama
ollama run "$OLLAMA_MODEL" "$PROMPT" 2>/dev/null

echo ""
echo "✅ Done. Cost: $0.00"
