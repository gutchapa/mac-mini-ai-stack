#!/usr/bin/env python3
"""
workflow-agent.py - Workflow-first app builder for coding agents.

Converts your plain-English app description into a structured workflow,
then feeds it to coding agents (DeepSeek, Kimi, Gemma 4, etc.)

Usage:
  workflow-agent.py new "school registration app"
  workflow-agent.py edit                        # Modify existing workflow
  workflow-agent.py show                         # View current workflow
  workflow-agent.py export                       # Get the workflow JSON + prompt for coding agent
  workflow-agent.py snapshot                     # Save current workflow as a snapshot
  workflow-agent.py update                       # Compare snapshot vs current, generate incremental update prompt
"""
import json
import os
import sys
import urllib.request
import urllib.error
import ssl
from datetime import datetime
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".openclaw" / "logs" / "workflows"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
WORKFLOW_FILE = DATA_DIR / "current_workflow.json"
HISTORY_FILE = DATA_DIR / "history.json"

WORKFLOW_SYSTEM_PROMPT = """You output JSON only. Design workflow with nodes. Each node: id (string), type (start/step/decision/end), label, description, data_fields (array), next (string or null), transitions (array of {condition, target})."""

def call_deepseek(prompt, system=None, max_tokens=2500):
    """Call DeepSeek V4 Flash.
    Note: system prompt triggers empty response bug on deepseek-v4-flash. User prompt only."""
    if not DEEPSEEK_KEY:
        print("❌ DEEPSEEK_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    
    url = "https://api.deepseek.com/v1/chat/completions"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_KEY}")
    req.add_header("Content-Type", "application/json")
    
    messages = [{"role": "user", "content": prompt}]
    if system:
        # DeepSeek V4 Flash has a bug with system prompts (returns empty).
        # Prepend system content into the user message instead.
        messages[0]["content"] = f"{system}\n\n{prompt}"
    
    data = {
        "model": "deepseek-v4-flash",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, json.dumps(data).encode(), timeout=60, context=ctx) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"❌ DeepSeek HTTP {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ DeepSeek error: {type(e).__name__}: {e}", file=sys.stderr)
        return None

def parse_json_from_response(response):
    """Extract JSON from model response, handling markdown fences and truncated output."""
    if not response:
        return None
    import re
    
    # Try to find a complete JSON block with fences
    match = re.search(r'```(?:json)?\n(\{.*?\})```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # Try fences but no closing (truncated output)
    match = re.search(r'```(?:json)?\n(\{.*)', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # Try direct JSON parse
    try:
        return json.loads(response.strip())
    except:
        pass
    
    # Try finding any JSON object
    match = re.search(r'\{.*"nodes".*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    match = re.search(r'\{.*"workflow".*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    # Try to complete truncated JSON by finding first complete object
    try:
        # Accumulate braces
        text = response.strip()
        if text.startswith('```json'):
            text = text[7:].strip()
        if text.startswith('```'):
            text = text[3:].strip()
        
        depth = 0
        start = -1
        for i, c in enumerate(text):
            if c == '{':
                if start == -1:
                    start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except:
                        pass
    except:
        pass
    
    return None

def validate_workflow(wf):
    """Validate workflow structure."""
    errors = []
    
    if not isinstance(wf, dict) or "workflow" not in wf:
        wf = {"workflow": wf}
    
    w = wf.get("workflow", wf)
    nodes = w.get("nodes", w.get("steps", []))
    
    if not nodes:
        errors.append("No nodes/steps defined")
        return errors
    
    # Check for required fields
    for node in nodes:
        if "id" not in node:
            errors.append("Node missing 'id'")
        if "label" not in node:
            errors.append(f"Node {node.get('id','?')} missing 'label'")
        if node.get("type") == "decision" and "transitions" not in node:
            errors.append(f"Decision node '{node.get('id')}' missing 'transitions'")
        if node.get("type") == "step" and "next" not in node:
            # Allow missing 'next' if it's an end node
            pass
    
    # Check for unreachable nodes
    reachable = set()
    start = w.get("start")
    if start:
        current = start
        visited = set()
        while current and current not in visited:
            visited.add(current)
            reachable.add(current)
            node = next((n for n in nodes if n.get("id") == current), None)
            if not node:
                break
            if node.get("type") == "decision":
                for t in node.get("transitions", []):
                    reachable.add(t.get("target"))
            current = node.get("next")
        
        unreachable = [n["id"] for n in nodes if n["id"] not in reachable]
        if unreachable:
            errors.append(f"Unreachable nodes: {unreachable}")
    
    return errors

def new_workflow(args):
    """Create new workflow from description."""
    description = " ".join(args) if args else input("Describe your app: ")
    
    print(f"\n🤖 Generating workflow for: {description}")
    print("   (using DeepSeek V4 Flash)")
    
    prompt = f"Output JSON only. Workflow for: {description}. Nodes: id, type (start/step/decision/end), label, data_fields, next, transitions."
    
    print(f"  Prompt length: {len(prompt)} chars")
    response = call_deepseek(prompt)
    if not response:
        print("❌ DeepSeek returned no response")
        return
    
    print(f"  Response: {len(response)} chars")
    print(f"  First 200: {response[:200]}")
    
    workflow = parse_json_from_response(response)
    if not workflow:
        print("❌ Could not parse response into JSON")
        print(f"Raw:\n{response[:500]}")
        return
    
    print(f"  Parsed: {len(json.dumps(workflow))} chars")
    print(f"  Nodes: {len(workflow.get('workflow',workflow).get('nodes',[]))}")
    
    
    errors = validate_workflow(workflow)
    if errors:
        print(f"\n⚠️  Validation warnings:")
        for e in errors:
            print(f"  - {e}")
    
    with open(WORKFLOW_FILE, "w") as f:
        json.dump(workflow, f, indent=2)
    
    print(f"\n✅ Workflow saved to {WORKFLOW_FILE}")
    print_workflow(workflow)

def print_workflow(wf):
    """Pretty print workflow."""
    if not isinstance(wf, dict):
        wf = {"workflow": {"nodes": []}}
    
    w = wf.get("workflow", wf)
    nodes = w.get("nodes", w.get("steps", []))
    
    print("\n" + "="*60)
    print("📋 WORKFLOW OVERVIEW")
    print("="*60)
    
    for node in nodes:
        nid = node["id"]
        ntype = node.get("type", "step")
        label = node.get("label", nid)
        
        if ntype == "start":
            icon = "🟢"
        elif ntype == "end":
            icon = "🔴"
        elif ntype == "decision":
            icon = "❓"
        else:
            icon = "📄"
        
        print(f"\n{icon} [{nid}] {label} ({ntype})")
        
        if node.get("description"):
            print(f"   {node['description']}")
        
        if node.get("data_fields"):
            fields = node["data_fields"]
            if fields and isinstance(fields[0], dict):
                field_names = [f.get("name", str(f)) for f in fields[:6]]
            else:
                field_names = [str(f) for f in fields[:6]]
            print(f"   Fields: {', '.join(field_names)}")
            if len(fields) > 6:
                print(f"     ... and {len(fields)-6} more")
        
        if node.get("type") == "decision":
            for t in node.get("transitions", []):
                print(f"   → IF {t.get('condition','?')}: go to [{t.get('target','?')}]")
        elif node.get("next"):
            print(f"   → Next: [{node['next']}]")
    
    print("\n" + "="*60)

def edit_workflow(args):
    """Edit existing workflow — add/insert/remove nodes."""
    if not WORKFLOW_FILE.exists():
        print("❌ No workflow found. Run `new` first.")
        return
    
    with open(WORKFLOW_FILE) as f:
        workflow = json.load(f)
    
    w = workflow.get("workflow", workflow)
    nodes = w.get("nodes", w.get("steps", []))
    
    print("\n🖊️  WORKFLOW EDITOR")
    print("Commands:")
    print("  add <after_node_id> <type> <label>   — Add new node")
    print("  remove <node_id>                     — Remove node")
    print("  edit <node_id> <field>:<value>       — Edit node field")
    print("  show                                  — View current workflow")
    print("  done                                  — Save and exit")
    print()
    
    action = " ".join(args) if args else input("workflow> ").strip()
    
    if action.startswith("add "):
        parts = action.split(" ", 2)
        if len(parts) < 3:
            print("Usage: add <after_node_id> <type> <label>")
            return
        after_id, ntype = parts[1], parts[2].split()[0]
        label = " ".join(parts[2].split()[1:])
        
        new_id = f"{label.lower().replace(' ','_')}"
        new_node = {
            "id": new_id,
            "type": ntype if ntype in ["step", "decision", "end"] else "step",
            "label": label,
            "next": None,
            "data_fields": [] if ntype == "step" else None
        }
        if ntype == "decision":
            new_node["transitions"] = [
                {"condition": "yes", "target": None, "label": "Yes"},
                {"condition": "no", "target": None, "label": "No"}
            ]
            del new_node["data_fields"]
            del new_node["next"]
        
        # Find insertion point
        for i, node in enumerate(nodes):
            if node["id"] == after_id:
                nodes.insert(i + 1, new_node)
                print(f"✅ Added '{new_id}' after '{after_id}'")
                break
        
        with open(WORKFLOW_FILE, "w") as f:
            json.dump(workflow, f, indent=2)
        
    elif action.startswith("remove "):
        rid = action.split(" ", 1)[1]
        nodes[:] = [n for n in nodes if n["id"] != rid]
        print(f"✅ Removed '{rid}'")
        with open(WORKFLOW_FILE, "w") as f:
            json.dump(workflow, f, indent=2)
    
    elif action.startswith("edit "):
        parts = action.split(" ", 2)
        if len(parts) < 3:
            print("Usage: edit <node_id> <field>:<value>")
            return
        eid = parts[1]
        field_val = parts[2]
        field, _, value = field_val.partition(":")
        
        for node in nodes:
            if node["id"] == eid:
                node[field] = value
                print(f"✅ Set {eid}.{field} = {value}")
                break
        
        with open(WORKFLOW_FILE, "w") as f:
            json.dump(workflow, f, indent=2)
    
    elif action == "show" or action == "view":
        print_workflow(workflow)
    
    elif action == "done" or action == "exit":
        print("✅ Saved")
        return
    
    else:
        print(f"Unknown: {action}")
        edit_workflow([])

def generate_system_prompt(workflow):
    """Generate a complete system prompt for the coding agent."""
    w = workflow.get("workflow", workflow)
    nodes = w.get("nodes", w.get("steps", []))
    
    app_name = w.get("name", w.get("description", "Application"))[:60]
    
    # Build constraints and rules from the workflow
    screens = [n for n in nodes if n.get("type") in ("step", "start")]
    decisions = [n for n in nodes if n.get("type") == "decision"]
    all_fields = []
    for n in nodes:
        for f in n.get("data_fields", []):
            if isinstance(f, dict):
                all_fields.append(f.get("name", str(f)))
            else:
                all_fields.append(str(f))
    
    lines = []
    lines.append(f"""You are building: {app_name}

## ARCHITECTURE — Read This First

This application follows a strict workflow defined below. Every screen, decision point, and data field is pre-defined. Do NOT add features outside this workflow unless asked.

## WORKFLOW NODES
""")
    
    for node in nodes:
        ntype = node.get("type", "step")
        nid = node["id"]
        label = node.get("label", nid)
        desc = node.get("description", "")
        
        if ntype == "start":
            lines.append(f"\n### 🟢 [{nid}] START — {label}")
        elif ntype == "end":
            lines.append(f"\n### 🔴 [{nid}] END — {label}")
        elif ntype == "decision":
            lines.append(f"\n### ❓ [{nid}] DECISION — {label}")
        else:
            lines.append(f"\n### 📄 [{nid}] SCREEN — {label}")
        
        if desc:
            lines.append(f"> {desc}")
        
        if node.get("data_fields"):
            fields = node["data_fields"]
            if fields and isinstance(fields[0], dict):
                field_names = [f.get("name", str(f)) for f in fields]
            else:
                field_names = [str(f) for f in fields]
            lines.append(f"\n**Fields to collect:**")
            for fn in field_names:
                lines.append(f"  - `{fn}`")
        
        if ntype == "decision":
            lines.append(f"\n**Branching:**")
            for t in node.get("transitions", []):
                lines.append(f"  - IF **{t['condition']}** → Go to `[{t['target']}]`")
        elif node.get("next"):
            lines.append(f"\n**→ Next step:** `[{node['next']}]`")
    
    
    lines.append(f"""

## RULES

1. Follow the workflow in order. Do not skip steps.
2. Each decision point must be implemented as a branch (if/else or switch).
3. Collect ALL data fields listed in each step before proceeding.
4. Validate inputs at each step before moving to the next.
5. Allow navigation back to previous steps (undo/edit).
6. Show clear success/error states after each action.
""")
    
    return "\n".join(lines)


def take_snapshot(workflow, label="snapshot"):
    """Save a snapshot of current workflow before changes."""
    snapshot_dir = DATA_DIR / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_label = label.lower().replace(" ", "_")[:30]
    filename = f"{timestamp}_{clean_label}.json"
    filepath = snapshot_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(workflow, f, indent=2)
    
    # Also save as latest.json for easy reference
    latest_path = snapshot_dir / "latest.json"
    with open(latest_path, "w") as f:
        json.dump(workflow, f, indent=2)
    
    return filepath


def diff_workflows(old_wf, new_wf):
    """Compare two workflows and return added, removed, and changed nodes."""
    def normalize_ids(workflow):
        w = workflow.get("workflow", workflow)
        nodes = w.get("nodes", w.get("steps", []))
        return {n["id"]: n for n in nodes}
    
    old_nodes = normalize_ids(old_wf)
    new_nodes = normalize_ids(new_wf)
    
    old_ids = set(old_nodes.keys())
    new_ids = set(new_nodes.keys())
    
    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    common_ids = new_ids & old_ids
    
    changed = []
    for nid in sorted(common_ids):
        if old_nodes[nid] != new_nodes[nid]:
            changed.append(new_nodes[nid])
    
    added = [new_nodes[nid] for nid in sorted(added_ids)]
    removed = [old_nodes[nid] for nid in sorted(removed_ids)]
    
    return {
        "added": added,
        "removed": removed,
        "changed": changed
    }


def update_workflow(args):
    """Update existing codebase based on workflow changes.
    
    Compares current workflow against previous snapshot and generates
    targeted instructions for the coding agent to apply changes
    incrementally rather than rewriting the entire app.
    """
    # Check current workflow exists
    if not WORKFLOW_FILE.exists():
        print("❌ No current workflow found. Create one first with `new`.")
        return
    
    with open(WORKFLOW_FILE) as f:
        current_workflow = json.load(f)
    
    # Find previous snapshot
    snapshot_dir = DATA_DIR / "snapshots"
    latest_snapshot = snapshot_dir / "latest.json"
    
    if not latest_snapshot.exists():
        print("❌ No previous snapshot found. Take one first with `workflow-agent.py snapshot`.")
        print("   (The first snapshot is your baseline. After that, edit the workflow and run `update`.)")
        return
    
    with open(latest_snapshot) as f:
        previous_workflow = json.load(f)
    
    # Do the diff
    diff = diff_workflows(previous_workflow, current_workflow)
    
    # Determine app name for context
    w = current_workflow.get("workflow", current_workflow)
    app_name = w.get("name", w.get("description", "Application"))[:60]
    old_w = previous_workflow.get("workflow", previous_workflow)
    
    new_node_count = len(diff["added"])
    removed_node_count = len(diff["removed"])
    changed_node_count = len(diff["changed"])
    
    total_current = len(w.get("nodes", w.get("steps", [])))
    total_before = len(old_w.get("nodes", old_w.get("steps", [])))
    
    print("\n" + "="*60)
    print("🔄 WORKFLOW UPDATE — DIFF REPORT")
    print("="*60)
    print(f"  App:    {app_name}")
    print(f"  Before: {total_before} nodes")
    print(f"  After:  {total_current} nodes")
    print(f"  Added:   {new_node_count}")
    print(f"  Removed: {removed_node_count}")
    print(f"  Changed: {changed_node_count}")
    
    # Build the update prompt
    prompt_parts = [
        "# INCREMENTAL WORKFLOW UPDATE",
        f"",
        f"**Do NOT rewrite the application from scratch. Apply only the changes below.**",
        f"",
        f"App: {app_name}",
        f"",
        f"---",
        f"",
    ]
    
    if diff["added"]:
        prompt_parts.extend([
            "## 🆕 NEW NODES TO ADD",
            f"Add {new_node_count} new node(s) to the existing code:",
            ""
        ])
        for node in diff["added"]:
            prompt_parts.append(f"### [{node['id']}] ({node.get('type', 'step')}) — {node.get('label', node['id'])}")
            if node.get("description"):
                prompt_parts.append(f">{node['description']}")
            if node.get("data_fields"):
                prompt_parts.append("")
                prompt_parts.append("Data fields:")
                for f in node["data_fields"]:
                    fname = f.get("name", f) if isinstance(f, dict) else f
                    prompt_parts.append(f"  - `{fname}`")
            if node.get("type") == "decision":
                prompt_parts.append("")
                prompt_parts.append("Branches:")
                for t in node.get("transitions", []):
                    prompt_parts.append(f"  - IF **{t['condition']}** → `[{t['target']}]`")
            elif node.get("next"):
                prompt_parts.append(f"")
                prompt_parts.append(f"→ Next step: `[{node['next']}]`")
            prompt_parts.append("")
    
    if diff["changed"]:
        prompt_parts.extend([
            "## 🔄 CHANGED NODES TO MODIFY",
            f"Update {changed_node_count} existing node(s):",
            ""
        ])
        for node in diff["changed"]:
            # Get old version for context
            old_w = previous_workflow.get("workflow", previous_workflow)
            old_nodes_list = old_w.get("nodes", old_w.get("steps", []))
            old_node = next((n for n in old_nodes_list if n["id"] == node["id"]), None)
            
            prompt_parts.append(f"### [{node['id']}] — {node.get('label', node['id'])}")
            prompt_parts.append(f"")
            prompt_parts.append("```diff")
            
            # Generate a simple text diff for the node fields
            if old_node:
                old_json = json.dumps(old_node, indent=2, ensure_ascii=False)
                new_json = json.dumps(node, indent=2, ensure_ascii=False)
                old_lines = old_json.split("\n")
                new_lines = new_json.split("\n")
                
                import difflib
                for line in difflib.unified_diff(old_lines, new_lines, 
                                                 fromfile=f"old/{node['id']}", 
                                                 tofile=f"new/{node['id']}",
                                                 lineterm=""):
                    prompt_parts.append(line)
            else:
                prompt_parts.append(f"  (could not retrieve old version)")
            
            prompt_parts.append("```")
            prompt_parts.append("")
    
    if diff["removed"]:
        prompt_parts.extend([
            "## ❌ REMOVED NODES TO DELETE",
            f"Remove {removed_node_count} node(s) and their associated code:",
            ""
        ])
        for node in diff["removed"]:
            prompt_parts.append(f"- `[{node['id']}]` {node.get('label', node['id'])}")
            if node.get("description"):
                prompt_parts.append(f"  - _{node['description']}_")
        prompt_parts.append("")
    
    if not diff["added"] and not diff["changed"] and not diff["removed"]:
        prompt_parts.append("## ℹ️ No changes detected — the workflow is identical to the last snapshot.")
        prompt_parts.append("")
    
    prompt_parts.extend([
        "---",
        "",
        "## SUMMARY",
        f"- Total nodes before: {total_before}",
        f"- Total nodes after:  {total_current}",
        f"- Net change: {'+' if total_current > total_before else ''}{total_current - total_before}",
        "",
        "## INSTRUCTIONS",
        "1. **Only modify code related to the listed nodes. Do not touch unrelated parts.**",
        "2. **Do NOT rewrite existing screens or components unless explicitly listed as CHANGED.**",
        "3. Add new screens/components for ADDED nodes.",
        "4. Update navigation/routing to accommodate removed nodes.",
        "5. Preserve all existing functionality intact.",
        "6. Ensure backward compatibility where possible.",
    ])
    
    update_prompt = "\n".join(prompt_parts)
    
    # Save update prompt to file
    update_file = DATA_DIR / "update_prompt.md"
    with open(update_file, "w") as f:
        f.write(update_prompt)
    
    print()
    print("="*60)
    print("📋 GENERATED UPDATE PROMPT")
    print("="*60)
    print(update_prompt)
    print(f"\n✅ Update prompt saved to {update_file}")
    print()
    print("⚠️  Don't forget to take a NEW snapshot after making changes!")
    print("   Run: workflow-agent.py snapshot")
    print()


def snapshot_workflow(args):
    """Take a manual snapshot of the current workflow."""
    if not WORKFLOW_FILE.exists():
        print("❌ No workflow found.")
        return
    
    with open(WORKFLOW_FILE) as f:
        workflow = json.load(f)
    
    label = " ".join(args) if args else "manual"
    filepath = take_snapshot(workflow, label)
    print(f"✅ Snapshot saved: {filepath}")


def export_workflow(args):
    """Export workflow as a structured prompt for coding agents."""
    if not WORKFLOW_FILE.exists():
        print("❌ No workflow found. Create one first with `new`.")
        return
    
    with open(WORKFLOW_FILE) as f:
        workflow = json.load(f)
    
    print("\n📦 EXPORTING WORKFLOW FOR CODING AGENT")
    print("="*60)
    
    # Generate the system prompt (for agent initialization)
    system_prompt = generate_system_prompt(workflow)
    
    # Generate the coding prompt (step-by-step)
    w = workflow.get("workflow", workflow)
    nodes = w.get("nodes", w.get("steps", []))
    
    prompt_lines = [
        "## Application Workflow",
        "",
        "Build this application following the workflow below. Each node is a step or decision point.",
        "",
        "### Workflow Nodes",
        ""
    ]
    
    for node in nodes:
        ntype = node.get("type", "step")
        nid = node["id"]
        label = node.get("label", nid)
        desc = node.get("description", "")
        
        prompt_lines.append(f"**{nid}** ({ntype}): {label}")
        if desc:
            prompt_lines.append(f"> {desc}")
        if node.get("data_fields"):
            fields = node["data_fields"]
            if fields and isinstance(fields[0], dict):
                field_names = [f.get("name", str(f)) for f in fields]
            else:
                field_names = [str(f) for f in fields]
            prompt_lines.append(f"  Data fields: {', '.join(field_names)}")
        if ntype == "decision":
            for t in node.get("transitions", []):
                prompt_lines.append(f"  → IF {t['condition']} THEN [{t['target']}]")
        elif node.get("next"):
            prompt_lines.append(f"  → Next: [{node['next']}]")
        prompt_lines.append("")
    
    prompt_lines.append("")
    prompt_lines.append("### Full Workflow JSON")
    prompt_lines.append("")
    prompt_lines.append("```json")
    prompt_lines.append(json.dumps(workflow, indent=2))
    prompt_lines.append("```")
    
    prompt = "\n".join(prompt_lines)
    
    # Full export: system prompt + workflow prompt
    full_export = f"""# SYSTEM PROMPT (for agent initialization)
```
{system_prompt}
```

# WORKFLOW INSTRUCTIONS (for step-by-step coding)
{prompt}
"""
    
    # Save both
    export_file = DATA_DIR / "workflow_prompt.md"
    with open(export_file, "w") as f:
        f.write(full_export)
    
    sys_prompt_file = DATA_DIR / "system_prompt.md"
    with open(sys_prompt_file, "w") as f:
        f.write(system_prompt)
    try:
        viewer_path = Path(__file__).parent / "workflow-viewer.html"
        desktop_html = Path.home() / "Desktop" / "current-workflow.html"
        if viewer_path.exists() and workflow:
            viewer = viewer_path.read_text()
            workflow_json_escaped = json.dumps(workflow)
            injection = f"\nconst WORKFLOW = {workflow_json_escaped};\nwindow.addEventListener('DOMContentLoaded', () => renderWorkflow(WORKFLOW));\n"
            standalone = viewer.replace("// Check for workflow in URL hash", 
                f"// Auto-load embedded workflow\n{injection}\n// Check for workflow in URL hash")
            desktop_html.write_text(standalone)
            print(f"\n🖥️  Visual workflow: open ~/Desktop/current-workflow.html in Safari")
    except Exception as e:
        print(f"  (visual generation skipped: {e})")
    
    print(full_export)
    print(f"\n✅ System prompt saved to {sys_prompt_file}")
    print(f"✅ Workflow prompt saved to {export_file}")
    print(f"\n📋 To use: feed the system prompt as initial context, then workflow prompt for coding.")
    print(f"🖥️  Visual: open ~/Desktop/current-workflow.html")

def show_workflow(args):
    """Show current workflow."""
    if not WORKFLOW_FILE.exists():
        print("❌ No workflow found.")
        return
    
    with open(WORKFLOW_FILE) as f:
        workflow = json.load(f)
    
    print_workflow(workflow)

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "new":
        new_workflow(args)
    elif command == "edit":
        edit_workflow(args)
    elif command == "show" or command == "view":
        show_workflow(args)
    elif command == "export":
        export_workflow(args)
    elif command == "update":
        update_workflow(args)
    elif command == "snapshot":
        snapshot_workflow(args)
    else:
        print(f"Unknown: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
