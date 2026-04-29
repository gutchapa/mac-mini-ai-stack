#!/usr/bin/env python3
"""
model-cmp.py - Side-by-side comparison of DeepSeek V4 Flash, DeepSeek Reasoner, and Gemma 4.
"""
import json, urllib.request, urllib.error, ssl, time, sys, subprocess, re, os
from pathlib import Path

WORKFLOW = {
  "nodes": [
    {"id":"1","type":"step","label":"Create Task","description":"Admin fills in task details: title, description, priority, assignee, deadline to date.","data_fields":["title","description","priority","assignee","deadline"],"next":"2"},
    {"id":"2","type":"decision","label":"Validate Task","transitions":[{"condition":"Valid","target":"3"},{"condition":"Invalid","target":"4"}]},
    {"id":"3","type":"step","label":"Save Task","data_fields":[],"next":"5"},
    {"id":"4","type":"step","label":"Show Validation Error","data_fields":[],"next":"1"},
    {"id":"5","type":"step","label":"Notify Assignee","data_fields":[],"next":"6"},
    {"id":"6","type":"step","label":"Staff Select Task","data_fields":["task_id"],"next":"7"},
    {"id":"7","type":"step","label":"Update Status","data_fields":["new_status"],"next":"8"},
    {"id":"8","type":"decision","label":"Validate Status Transition","transitions":[{"condition":"Allowed","target":"9"},{"condition":"Denied","target":"7"}],"next":"8"},
    {"id":"9","type":"step","label":"Update Task Status","data_fields":[],"next":"10"},
    {"id":"10","type":"step","label":"Notify Admin","data_fields":[],"next":"11"},
    {"id":"11","type":"step","label":"Add Comment","data_fields":["comment_text"],"next":"12"},
    {"id":"12","type":"decision","label":"Check Overdue","transitions":[{"condition":"Overdue","target":"13"},{"condition":"Not overdue","target":"14"}]},
    {"id":"13","type":"step","label":"Notify Overdue","data_fields":[],"next":"14"},
    {"id":"14","type":"step","label":"View Dashboard","data_fields":["filter_option"]}
  ]
}

SYSTEM_PROMPT = """
You are building: School Admin Todo List Application

Workflow:
""" + json.dumps(WORKFLOW, indent=2) + """

Rules:
1. SINGLE HTML FILE with embedded CSS and JS
2. Use localStorage for persistence
3. Two views: Admin (creates tasks, dashboard) and Staff (updates status, comments)
4. Show notifications for overdue tasks and status changes
5. Dashboard: total tasks, by status, by assignee, overdue filter
6. Valid status transitions: pending -> in_progress -> completed, or blocked
7. Include all data fields listed for each step
8. Professional school theme

Output ONLY the HTML code. No explanation.
"""

RESULTS_DIR = Path.home() / ".openclaw" / "logs" / "benchmarks"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def test_deepseek(variant):
    key = "DEEPSEEK_API_KEY"
    model = "deepseek-v4-flash" if variant == "flash" else "deepseek-v4-pro"
    label = "DeepSeek V4 Flash" if variant == "flash" else "DeepSeek V4 Pro"
    
    print("\n" + "="*60)
    print("  🚀 " + label)
    print("="*60)
    
    req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions", method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": SYSTEM_PROMPT.strip()}],
        "max_tokens": 8000,
        "temperature": 0,
        "stream": False
    })
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, data.encode(), timeout=180, context=ctx) as resp:
            raw = resp.read()
            elapsed = time.time() - start
            result = json.loads(raw.decode())
            content = result["choices"][0]["message"]["content"]
            
            html = content
            m = re.search(r'```(?:html)?\n(.*?)\n```', content, re.DOTALL)
            if m:
                html = m.group(1)
            
            lines = html.count("\n")
            out = RESULTS_DIR / ("deepseek-" + variant + ".html")
            out.write_text(html)
            
            print("  ⏱  {:.1f}s | {} chars | {} lines".format(elapsed, len(content), lines))
            
            return {"model": label, "elapsed": elapsed, "chars": len(content), "lines": lines, "file": str(out), "html": html}
    except urllib.error.HTTPError as e:
        print("  ❌ HTTP {}: {}".format(e.code, e.read().decode()[:200]))
        return {"model": label, "error": str(e.code)}
    except Exception as e:
        print("  ❌ {}: {}".format(type(e).__name__, str(e)))
        return {"model": label, "error": str(e)}

def test_gemma4():
    print("\n" + "="*60)
    print("  🚀 Gemma 4 (local)")
    print("="*60)
    
    data = json.dumps({
        "model": "gemma4:e4b-q4",
        "prompt": SYSTEM_PROMPT.strip(),
        "stream": False,
        "options": {"num_ctx": 8192, "temperature": 0}
    })
    
    start = time.time()
    try:
        req = urllib.request.Request("http://localhost:11434/api/generate", method="POST", data=data.encode())
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=600) as resp:
            elapsed = time.time() - start
            result = json.loads(resp.read().decode())
            content = result.get("response", "")
            
            html = content
            m = re.search(r'```(?:html)?\n(.*?)\n```', content, re.DOTALL)
            if m:
                html = m.group(1)
            
            lines = html.count("\n")
            out = RESULTS_DIR / "gemma4.html"
            out.write_text(html)
            
            print("  ⏱  {:.1f}s | {} chars | {} lines".format(elapsed, len(content), lines))
            
            return {"model": "Gemma 4 (local)", "elapsed": elapsed, "chars": len(content), "lines": lines, "file": str(out), "html": html}
    except Exception as e:
        print("  ❌ {}: {}".format(type(e).__name__, str(e)))
        return {"model": "Gemma 4 (local)", "error": str(e)}

def analyze_html(html):
    html_lower = html.lower()
    return {
        "has_form": "form" in html_lower or "input" in html_lower,
        "has_css": "<style" in html or 'style="' in html,
        "has_localstorage": "localstorage" in html_lower,
        "has_multiuser": "admin" in html_lower,
        "has_js": "<script" in html or "function" in html_lower,
        "has_notifications": "notif" in html_lower,
        "has_dashboard": "dashboard" in html_lower,
        "has_status": "pending" in html_lower or "in_progress" in html_lower or "completed" in html_lower,
        "complete_html": html.strip().startswith("<!DOCTYPE") or html.strip().startswith("<html") or html.strip().startswith("<!"),
    }

def show_table(results):
    print("\n" + "="*90)
    print("  📊 MODEL COMPARISON RESULTS")
    print("="*90)
    
    h = ["Model", "Time", "Chars", "Lines", "Form", "CSS", "localStorage", "Users", "Notif", "Dash", "Status"]
    hr = "  " + "-"*87
    print()
    
    for r in results:
        print("{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|".format(
            r.get("model","?").ljust(20),
            ("{:.1f}s".format(r.get("elapsed",0)) if "elapsed" in r else "FAIL").center(8),
            ("{:,}".format(r.get("chars",0)) if "chars" in r else "---").center(8),
            (str(r.get("lines","-"))).center(6),
            ("Y" if r.get("has_form") else "N").center(5),
            ("Y" if r.get("has_css") else "N").center(4),
            ("Y" if r.get("has_localstorage") else "N").center(11),
            ("Y" if r.get("has_multiuser") else "N").center(6),
            ("Y" if r.get("has_notifications") else "N").center(5),
            ("Y" if r.get("has_dashboard") else "N").center(5),
            ("✅" if "error" not in r else "❌ " + r.get("error","")[:10])
        ))
    
    print(hr)

if __name__ == "__main__":
    results = []
    
    for r in [test_deepseek("flash"), test_deepseek("reasoner"), test_gemma4()]:
        if "error" not in r and "html" in r and r["html"]:
            a = analyze_html(r["html"])
            r.update(a)
        results.append(r)
    
    show_table(results)
    
    results_file = RESULTS_DIR / "comparison.json"
    clean = []
    for r in results:
        c = {k: v for k, v in r.items() if k != "html"}
        clean.append(c)
    with open(results_file, "w") as f:
        json.dump({"tested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "results": clean}, f, indent=2)
    print("\n💾 Full results: {}".format(results_file))
