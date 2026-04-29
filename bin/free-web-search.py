#!/usr/bin/env python3
"""
free-web-search.py - Zero-cost web search using SearXNG + local Ollama
Usage:
  free-web-search.py "your search query"
  free-web-search.py --list-instances    # Show available SearXNG instances
  free-web-search.py --model gemma4:e4b-q4 "query"   # Use specific model
"""
import sys
import os
import re
import json
import urllib.request
import urllib.parse
import subprocess
import ssl

# Public SearXNG instances (no API key needed)
# These are community-run meta-search engines
SEARXNG_INSTANCES = [
    "https://search.sapti.me",
    "https://search.bus-hit.me",
    "https://search.privacyredirect.com",
    "https://search.rhscz.eu",
    "https://search.unlocked.link",
]

def searxng_search(query, instance_url):
    """Search using a SearXNG instance."""
    params = {
        'q': query,
        'format': 'json',
        'language': 'en',
    }
    url = f"{instance_url}/search?{urllib.parse.urlencode(params)}"
    
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    )
    
    try:
        # Allow self-signed certs (some instances use them)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('results', [])
    except Exception as e:
        print(f"  ⚠️  {instance_url} failed: {str(e)[:50]}")
        return []

def fetch_page_text(url, max_chars=3000):
    """Fetch and extract text from a URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Simple HTML to text
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text[:max_chars]
    except Exception as e:
        return f"[Could not fetch: {str(e)[:50]}]"

def ollama_synthesize(query, sources, model="gemma4:e4b-q4"):
    """Use local Ollama to synthesize search results."""
    
    # Build context from sources
    context_parts = []
    for i, source in enumerate(sources[:3], 1):
        title = source.get('title', 'No title')
        url = source.get('url', 'No URL')
        content = source.get('content', '')
        context_parts.append(f"SOURCE {i}:\nTitle: {title}\nURL: {url}\nContent: {content[:800]}\n")
    
    context = "\n".join(context_parts)
    
    prompt = f"""Based on the following web search results about "{query}", provide a comprehensive, accurate answer. 
If the results are insufficient, say so. Cite sources by number [1], [2], etc.

{context}

Question: {query}

Answer:"""
    
    try:
        result = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "❌ Ollama timed out. Model may be loading (first run takes ~30s)."
    except FileNotFoundError:
        return "❌ Ollama not found. Is it installed and in PATH?"
    except Exception as e:
        return f"❌ Error running Ollama: {e}"

def list_instances():
    """Test which SearXNG instances are working."""
    print("Testing SearXNG instances...")
    for url in SEARXNG_INSTANCES:
        results = searxng_search("test", url)
        status = "✅ Working" if results else "❌ Down/Blocked"
        print(f"  {status}: {url}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    if sys.argv[1] == '--list-instances':
        list_instances()
        return
    
    # Parse arguments
    model = "gemma4:e4b-q4"
    args = sys.argv[1:]
    
    if args[0] == '--model':
        model = args[1]
        args = args[2:]
    
    query = ' '.join(args)
    
    print(f"🔍 Free web search: \"{query}\"")
    print(f"🤖 Using Ollama model: {model}")
    print()
    
    # Try each instance until we get results
    all_results = []
    for instance in SEARXNG_INSTANCES:
        print(f"Trying {instance}...")
        results = searxng_search(query, instance)
        if results:
            all_results = results
            print(f"✅ Got {len(results)} results")
            break
    
    if not all_results:
        print("\n❌ All SearXNG instances failed.")
        print("Possible reasons:")
        print("  - Network issues")
        print("  - All instances are down")
        print("  - DuckDuckGo/Google blocking the instances")
        print("\nTry again later or use --list-instances to check status.")
        sys.exit(1)
    
    # Fetch content from top results
    print("\n📄 Fetching content from top results...")
    sources = []
    for result in all_results[:3]:
        url = result.get('url', '')
        title = result.get('title', 'No title')
        
        if url:
            print(f"  → {title[:60]}...")
            content = fetch_page_text(url)
            sources.append({
                'title': title,
                'url': url,
                'content': content
            })
    
    # Synthesize with Ollama
    print(f"\n🧠 Synthesizing with {model}...")
    print("=" * 60)
    answer = ollama_synthesize(query, sources, model)
    print(answer)
    print("=" * 60)
    
    print(f"\n✅ Done. Cost: $0.00 | Sources: {len(sources)}")
    
    # Log usage
    log_file = os.path.expanduser("~/.openclaw/web-search-usage.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    entry = {
        "timestamp": subprocess.run(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], capture_output=True, text=True).stdout.strip(),
        "tool": "free_web_search",
        "query": query,
        "tokens": 0,
        "cost_usd": 0.0,
        "model": model
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
