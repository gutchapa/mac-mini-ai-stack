#!/usr/bin/env python3
"""
claw-sweep.py - Lightweight issue/PR triage for your repos.
Architecture inspired by openclaw/clawsweeper but ~50x smaller.

Usage:
  claw-sweep.py plan                  # List open items
  claw-sweep.py review                # Fetch + DeepSeek review
  claw-sweep.py review --numbers 1,2  # Review specific items only
  claw-sweep.py report                # Show dashboard summary
  claw-sweep.py plan --save           # Save plan to disk
"""
import json
import os
import sys
import urllib.request
import urllib.error
import time
import ssl
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".openclaw" / "config"
DATA_DIR = Path.home() / ".openclaw" / "logs" / "sweep"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "claw-sweep.json"
PLAN_FILE = DATA_DIR / "plan.json"
REVIEWS_DIR = DATA_DIR / "reviews"
DASHBOARD_FILE = DATA_DIR / "dashboard.md"

CONFIG_DEFAULTS = {
    "repos": [
        {"owner": "RamEsh", "name": "paperclip-fork", "label": "Paperclip Fork"},
        {"owner": "gutchapa", "name": "dell-claw-mini", "label": "Dell Claw Mini"},
    ],
    "extra_repos": [
        {"owner": "openclaw", "name": "openclaw", "label": "OpenClaw Core"},
    ],
    "deepseek_model": "deepseek-v4-flash",
    "deepseek_max_tokens": 1024,
    "review_policy": "Conservative: only propose close for: implemented on main, cannot reproduce, duplicate, stale+insufficient info.",
    "protected_labels": ["security", "beta-blocker", "release-blocker", "maintainer"],
    "stale_days": 60,
    "min_confidence_to_close": "high",
    "github_token_env": "GITHUB_TOKEN",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        # Merge with defaults
        merged = CONFIG_DEFAULTS.copy()
        merged.update(cfg)
        return merged
    return CONFIG_DEFAULTS.copy()

def get_gh_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENCLAWH_GH_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("⚠️  No GITHUB_TOKEN found. Set GITHUB_TOKEN env var for API access.", file=sys.stderr)
        print("    Without it, only public repos will work and rate limit is 60/hr.", file=sys.stderr)
    return token

def github_api(path, token=None, method="GET", data=None):
    """Call GitHub API with auth."""
    url = f"https://api.github.com/{path.lstrip('/')}"
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", "claw-sweep/1.0")
    req.add_header("Accept", "application/vnd.github+json")
    
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data).encode()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 403:
            print(f"  ⚠️  Rate limited: {body[:200]}", file=sys.stderr)
        elif e.code == 404:
            print(f"  ⚠️  Not found: {url}", file=sys.stderr)
        else:
            print(f"  ⚠️  HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠️  Error: {e}", file=sys.stderr)
        return None

def deepseek_api(prompt, config):
    """Call DeepSeek API for triage."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("  ❌ DEEPSEEK_API_KEY not set", file=sys.stderr)
        return None
    
    url = "https://api.deepseek.com/v1/chat/completions"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "claw-sweep/1.0")
    
    data = {
        "model": config["deepseek_model"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": config["deepseek_max_tokens"],
        "temperature": 0,
        "stream": False
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, json.dumps(data).encode(), timeout=30, context=ctx) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"  ❌ DeepSeek API error: {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ❌ DeepSeek error: {e}", file=sys.stderr)
        return None

def score_item(item):
    """Score an item for priority (like clawsweeper's reviewPriority)."""
    score = 0
    # Created recently = higher priority
    created = item.get("created_at", "")
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).days
            score += max(100 - age_days * 5, 0)  # newer = higher
        except:
            pass
    # Has comments = more discussion
    score += item.get("comments", 0) * 10
    # Has assignee = more active
    if item.get("assignee"):
        score += 30
    return score

def is_protected(item, config):
    """Check if item has protected labels."""
    labels = [l.get("name", "").lower() if isinstance(l, dict) else str(l).lower() for l in item.get("labels", [])]
    for pl in config["protected_labels"]:
        if pl.lower() in labels:
            return True, pl
    return False, None

def format_item_short(item):
    """Short one-line item description."""
    kind = "PR" if "pull_request" in item else "Issue"
    return f"[#{item['number']}] {kind}: {item['title']}"

def build_review_prompt(item, config):
    """Build the prompt for DeepSeek (like clawsweeper's promptFor)."""
    created = item.get("created_at", "unknown")
    updated = item.get("updated_at", "unknown")
    body = item.get("body", "") or "(no description)"
    comments = item.get("comments", 0)
    kind = "PR" if "pull_request" in item else "Issue"
    labels = ", ".join([l["name"] for l in item.get("labels", [])]) if item.get("labels") else "none"
    
    return f"""## Issue/PR to Review

**Repo:** {item.get('repo', 'unknown')}
**#{item['number']}**: {item['title']}
**Type:** {kind}
**Created:** {created}
**Updated:** {updated}
**Labels:** {labels}
**Comments:** {comments}

### Description
{body[:2000]}

### Comments (last 5)
{item.get('_comments_preview', '(no comments in preview)')}

---

### Task
Review this {kind} and decide. Respond with a JSON decision:

```json
{{
  "decision": "close" or "keep_open",
  "confidence": "high" or "medium" or "low",
  "close_reason": "implemented_on_main" or "cannot_reproduce" or "duplicate_or_superseded" or "stale_insufficient_info" or "incoherent" or "none",
  "summary": "Brief summary of what this item is about",
  "evidence": ["List key evidence points"],
  "risks": ["List risks of closing"],
  "best_solution": "What should actually be done"
}}
```

**Rules:**
- Only propose close if confidence is HIGH and reason is clear
- Protected labels ({config['protected_labels']}) = automatic KEEP OPEN
- Items older than {config['stale_days']} days with little info → stale close
- Maintainer-authored items → keep open
- For keep_open, suggest what needs to happen
"""

def fetch_item_details(owner, repo, number, token):
    """Fetch full item details + comments from GitHub."""
    item = github_api(f"repos/{owner}/{repo}/issues/{number}", token)
    if not item:
        return None
    
    item["repo"] = f"{owner}/{repo}"
    
    # Fetch comments
    comments = github_api(f"repos/{owner}/{repo}/issues/{number}/comments?per_page=5&sort=created&direction=desc", token)
    if comments:
        item["_comments"] = comments
        item["_comments_preview"] = "\n".join(
            [f"  [{c['user']['login']}]: {c['body'][:300]}" for c in reversed(comments[-5:])]
        )
    
    return item

# ─── Commands ─────────────────────────────────────────────────────────────────

def scan_local_repos(config):
    """Scan local repos for stale branches, uncommitted changes, etc."""
    print("\n📁 Scanning Local Repos...")
    findings = []
    
    for repo_cfg in config.get("local_repos", []):
        path = Path(repo_cfg["path"]).expanduser()
        label = repo_cfg.get("label", str(path))
        
        if not path.exists() or not (path / ".git").exists():
            continue
        
        repo_findings = []
        
        # 1. Check for uncommitted changes
        result = os.popen(f"cd {path} && git status --porcelain").read().strip()
        if result:
            lines = result.split("\n")
            modified = [l for l in lines if l.startswith(" M") or l.startswith("?")]
            staged = [l for l in lines if l.startswith("M")]
            if len(modified) + len(staged) > 10:
                repo_findings.append({
                    "type": "uncommitted",
                    "detail": f"{len(modified)} modified + {len(staged)} staged files"
                })
        
        # 2. Check for stale branches
        result = os.popen(f"cd {path} && git branch -vv | grep ': gone]'").read().strip()
        if result:
            branches = [l.strip() for l in result.split("\n") if l.strip()]
            if branches:
                repo_findings.append({
                    "type": "stale_branches",
                    "detail": f"{len(branches)} branches: {', '.join(b[:20] for b in branches[:5])}"
                })
        
        # 3. Check ahead/behind remote
        result = os.popen(f"cd {path} && git status -sb 2>/dev/null | head -3").read().strip()
        if "ahead" in result or "behind" in result:
            repo_findings.append({
                "type": "out_of_sync",
                "detail": result.strip()
            })
        
        # 4. Check for unmerged branches
        result = os.popen(f"cd {path} && git branch --no-merged 2>/dev/null | wc -l").read().strip()
        count = int(result.strip())
        if count > 2:
            repo_findings.append({
                "type": "unmerged_branches",
                "detail": f"{count} unmerged branches"
            })
        
        # 5. Check if gitignore exists
        if not (path / ".gitignore").exists():
            repo_findings.append({
                "type": "missing_gitignore",
                "detail": "No .gitignore"
            })
        
        if repo_findings:
            print(f"  📂 {label}: {len(repo_findings)} issues")
            for f in repo_findings:
                print(f"    ⚠️  {f['type']}: {f['detail']}")
                findings.append({
                    "repo": label,
                    "path": str(path),
                    **f
                })
        else:
            print(f"  ✅ {label}: clean")
    
    return findings


def plan_command(config, args):
    """List all open issues/PRs from configured repos (like clawsweeper's plan)."""
    token = get_gh_token()
    save_mode = any(a == "--save" for a in args)
    
    all_items = []
    
    repos = config.get("repos", []) + config.get("extra_repos", [])
    
    for repo in repos:
        owner, name = repo["owner"], repo["name"]
        label = repo.get("label", f"{owner}/{name}")
        print(f"\n📋 {label} ({owner}/{name}):")
        
        for state_type, type_label in [("issue", "Issues"), ("pr", "PRs")]:
            if state_type == "pr":
                path = f"repos/{owner}/{name}/pulls?state=open&per_page=50&sort=created&direction=desc"
            else:
                path = f"repos/{owner}/{name}/issues?state=open&per_page=50&sort=created&direction=desc"
            
            items = github_api(path, token)
            if items is None:
                continue
            
            # Filter out PRs from issues endpoint (GitHub returns both)
            if state_type == "issue":
                items = [i for i in items if "pull_request" not in i]
            
            for item in items:
                item["_repo_owner"] = owner
                item["_repo_name"] = name
                item["_repo_label"] = label
                item["_type"] = state_type
            
            all_items.extend(items)
            print(f"  {type_label}: {len(items)} open")
    
    # Sort by priority score
    all_items.sort(key=score_item, reverse=True)
    
    if save_mode:
        with open(PLAN_FILE, "w") as f:
            json.dump({"planned_at": datetime.now(timezone.utc).isoformat(), "items": all_items}, f, indent=2)
        print(f"\n📦 Plan saved to {PLAN_FILE}")
    
    return all_items

def review_command(config, args):
    """Review items with DeepSeek (like clawsweeper's review)."""
    token = get_gh_token()
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ DEEPSEEK_API_KEY not set. Cannot review.", file=sys.stderr)
        sys.exit(1)
    
    # Get items to review
    specific_numbers = None
    for a in args:
        if a.startswith("--numbers="):
            specific_numbers = [int(x.strip()) for x in a.split("=", 1)[1].split(",")]
    
    if specific_numbers:
        # Fetch specific items by number
        items_to_review = []
        for repo in config.get("repos", []):
            for num in specific_numbers:
                item = github_api(f"repos/{repo['owner']}/{repo['name']}/issues/{num}", token)
                if item:
                    item["repo"] = f"{repo['owner']}/{repo['name']}"
                    items_to_review.append(item)
                    break
    else:
        # Full plan → review
        if PLAN_FILE.exists():
            with open(PLAN_FILE) as f:
                plan = json.load(f)
            items_to_review = plan.get("items", [])
        else:
            print("📋 No plan found. Running plan first...")
            items_to_review = plan_command(config, ["--save"])
        
        # Only review first N (to save API cost)
        max_items = 10
        if len(items_to_review) > max_items:
            print(f"\n📊 {len(items_to_review)} items total. Reviewing top {max_items} by priority.")
            items_to_review = items_to_review[:max_items]
    
    print(f"\n🔍 Reviewing {len(items_to_review)} items with DeepSeek {config['deepseek_model']}...")
    
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    for i, item in enumerate(items_to_review, 1):
        number = item["number"]
        title = item["title"]
        owner = item.get("_repo_owner", item.get("repo", "").split("/")[0] if "/" in item.get("repo", "") else "?")
        name = item.get("_repo_name", item.get("repo", "").split("/")[1] if "/" in item.get("repo", "") else "?")
        repo_label = item.get("_repo_label", f"{owner}/{name}")
        kind = "PR" if "pull_request" in item else "Issue"
        
        print(f"\n  [{i}/{len(items_to_review)}] #{number} {kind}: {title[:60]}...")
        
        # Check protected labels
        protected, protected_by = is_protected(item, config)
        if protected:
            print(f"  ⛔ Protected by label: {protected_by} — keeping open")
            decision = {
                "decision": "keep_open",
                "confidence": "high",
                "close_reason": "none",
                "summary": f"Protected by label: {protected_by}",
                "evidence": [],
                "risks": [],
                "best_solution": "Auto-kept open (protected label)"
            }
        else:
            # Fetch full details + comments
            full_item = fetch_item_details(owner, name, number, token)
            if not full_item:
                print(f"  ⚠️  Could not fetch details for #{number}")
                continue
            
            # Build prompt and call DeepSeek
            prompt = build_review_prompt(full_item, config)
            
            # Truncate if too long
            max_prompt_len = 40000
            if len(prompt) > max_prompt_len:
                prompt = prompt[:max_prompt_len] + "\n\n[...truncated...]"
            
            print(f"  🤖 Asking DeepSeek...", end=" ", flush=True)
            response = deepseek_api(prompt, config)
            
            if response is None:
                print("❌ Failed")
                continue
            
            # Extract JSON from response
            try:
                # Find JSON block
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()
                
                decision = json.loads(json_str)
                print(f"→ {decision['decision']} ({decision['confidence']})")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Parse error: {e}")
                print(f"  Raw: {response[:200]}")
                decision = {
                    "decision": "keep_open",
                    "confidence": "low",
                    "close_reason": "none",
                    "summary": "Failed to parse AI decision",
                    "evidence": [],
                    "risks": ["AI response couldn't be parsed"],
                    "best_solution": "Manual review needed"
                }
        
        decision["number"] = number
        decision["title"] = title
        decision["repo"] = repo_label
        decision["kind"] = kind
        decision["url"] = item.get("html_url", f"https://github.com/{owner}/{name}/issues/{number}")
        decision["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        results.append(decision)
        
        # Save individual review file
        review_path = REVIEWS_DIR / f"{number}.md"
        with open(review_path, "w") as f:
            f.write(f"# Review: #{number} — {title}\n\n")
            f.write(f"**Repo:** {repo_label}\n")
            f.write(f"**URL:** {decision['url']}\n")
            f.write(f"**Reviewed at:** {decision['reviewed_at']}\n\n")
            f.write(f"## Decision\n\n")
            f.write(f"- **Decision:** {decision['decision']}\n")
            f.write(f"- **Confidence:** {decision['confidence']}\n")
            f.write(f"- **Close Reason:** {decision['close_reason']}\n\n")
            f.write(f"## Summary\n\n{decision['summary']}\n\n")
            if decision.get("evidence"):
                f.write(f"## Evidence\n\n")
                for e in decision["evidence"]:
                    f.write(f"- {e}\n")
                f.write("\n")
            if decision.get("risks"):
                f.write(f"## Risks\n\n")
                for r in decision["risks"]:
                    f.write(f"- {r}\n")
                f.write("\n")
            f.write(f"## Best Solution\n\n{decision['best_solution']}\n")
        
        # Sleep between reviews to avoid rate limits
        if i < len(items_to_review):
            time.sleep(1)
    
    # Save all results
    results_path = DATA_DIR / "latest_review.json"
    with open(results_path, "w") as f:
        json.dump({"reviewed_at": datetime.now(timezone.utc).isoformat(), "reviews": results}, f, indent=2)
    
    print(f"\n✅ Reviewed {len(results)} items. Reports in {REVIEWS_DIR}")
    return results

def report_command(config, args):
    """Generate dashboard summary (like clawsweeper's dashboard)."""
    results_path = DATA_DIR / "latest_review.json"
    
    # Load local scan findings
    local_findings = []
    local_file = DATA_DIR / "local_scan.json"
    if local_file.exists():
        with open(local_file) as f:
            local_data = json.load(f)
        local_findings = local_data.get("findings", [])
    if not results_path.exists():
        print("📋 No review results found. Run `review` first.")
        return
    
    with open(results_path) as f:
        data = json.load(f)
    
    reviews = data.get("reviews", [])
    
    close_count = sum(1 for r in reviews if r["decision"] == "close")
    keep_count = sum(1 for r in reviews if r["decision"] == "keep_open")
    high_conf = sum(1 for r in reviews if r["confidence"] == "high")
    
    lines = []
    lines.append("# 🧹 Claw Sweep Dashboard")
    lines.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|------:|")
    lines.append(f"| Total reviewed | {len(reviews)} |")
    lines.append(f"| Proposed close | {close_count} |")
    lines.append(f"| Keep open | {keep_count} |")
    lines.append(f"| High confidence | {high_conf} |")
    lines.append("")
    
    if local_findings:
        lines.append("\n## 🏠 Local Repo Health")
        lines.append(f"*{len(local_findings)} issues found*")
        lines.append("")
        lines.append(f"| Repo | Issue | Detail |")
        lines.append(f"|------|-------|--------|")
        for f in local_findings:
            lines.append(f"| {f['repo']} | {f['type']} | {f['detail']} |")
        lines.append("")
    
    if reviews:
        lines.append("## Items")
        lines.append("")
        for r in reviews:
            icon = "🗑️" if r["decision"] == "close" else "📌"
            lines.append(f"### {icon} [{r['repo']}] #{r['number']} — {r['title'][:80]}")
            status = "CLOSE" if r["decision"] == "close" else "KEEP OPEN"
            lines.append(f"**{status}** ({r['confidence']}) | {r['close_reason']}")
            lines.append(f"")
            lines.append(f"_{r['summary'][:200]}_")
            lines.append("")
    
    lines.append("---")
    lines.append(f"*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*")
    
    dashboard = "\n".join(lines)
    print(dashboard)
    
    # Save dashboard
    with open(DASHBOARD_FILE, "w") as f:
        f.write(dashboard)
    print(f"\n📊 Dashboard saved to {DASHBOARD_FILE}")

def init_config(config, args):
    """Initialize or show config."""
    if CONFIG_FILE.exists():
        print(f"Config exists at {CONFIG_FILE}")
        with open(CONFIG_FILE) as f:
            print(json.dumps(json.load(f), indent=2))
        return
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG_DEFAULTS, f, indent=2)
    print(f"✅ Created default config at {CONFIG_FILE}")
    print("   Edit to add your repos, labels, etc.")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    config = load_config()
    
    if command == "plan":
        plan_command(config, args)
    elif command == "review":
        review_command(config, args)
    elif command == "local":
        results = scan_local_repos(config)
        local_file = DATA_DIR / "local_scan.json"
        with open(local_file, "w") as f:
            json.dump({"scanned_at": datetime.now(timezone.utc).isoformat(), "findings": results}, f, indent=2)
        print(f"\n💾 Saved to {local_file}")
    elif command == "report":
        report_command(config, args)
    elif command == "init":
        init_config(config, args)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
