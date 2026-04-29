#!/usr/bin/env python3
import os
import os.path
"""Coder Agent with Kimi Code API - High performance cloud model"""
import json, requests, sys, os, time, subprocess

WORKSPACE = os.path.expanduser('~/.openclaw/workspace')
MODEL = 'kimi-code'
API_URL = 'https://api.kimi.com/coding/v1/messages'
# Using the key found in your PI_SETUP.md / crewai scripts
API_KEY = os.getenv("KIMI_API_KEY", "sk-kimi-l0Ju2tcVDDPnhM1YwyYls2k3I4n8RVhnNNIs32EfDmLSmqeGLoSgXxHuxshjWNqo")

def log_metrics(task_id, tokens_in, tokens_out, eval_time, cost):
    try:
        subprocess.run([f'{WORKSPACE}/llm-observability.sh', 'log', task_id, 'coder', MODEL, 
                       str(tokens_in), str(tokens_out), str(eval_time), str(cost)], capture_output=True)
    except:
        pass # Best effort

def call_kimi(prompt):
    start = time.time()
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert Python programmer. Write clean, working code with comments. Only output code."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        elapsed = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            
            # Kimi Code API uses Anthropic-style 'content' array
            if 'content' in data and isinstance(data['content'], list):
                content = ""
                for part in data['content']:
                    if part.get('type') == 'text':
                        content += part.get('text', '')
                content = content.strip()
            elif 'choices' in data:
                content = data['choices'][0]['message']['content'].strip()
            else:
                return {'response': f"API Error: Unexpected response format: {json.dumps(data)}", 'tokens_in': 0, 'tokens_out': 0, 'eval_time': 0, 'success': False}

            # Detect language and filename hint
            extension = ".py"
            if "```typescript" in content or "```tsx" in content:
                extension = ".tsx"
            elif "```javascript" in content or "```jsx" in content:
                extension = ".jsx"
            elif "```html" in content:
                extension = ".html"
            
            if "```" in content:
                # Get the content inside the first code block
                content = content.split("```")[1]
                # Strip the language name if present (e.g., "python\nprint(1)")
                if "\n" in content:
                    first_line = content.split("\n")[0].strip()
                    if first_line in ["python", "typescript", "tsx", "javascript", "jsx", "html", "css", "bash", "sh"]:
                        content = content.split("\n", 1)[1]
                content = content.split("```")[0].strip()
                
            return {
                'response': content,
                'extension': extension,
                'tokens_in': data.get('usage', {}).get('prompt_tokens', 0),
                'tokens_out': data.get('usage', {}).get('completion_tokens', 0),
                'eval_time': elapsed,
                'success': True
            }
        else:
            return {'response': f"API Error {response.status_code}: {response.text}", 'tokens_in': 0, 'tokens_out': 0, 'eval_time': 0, 'success': False}
    except Exception as e:
        return {'response': str(e), 'tokens_in': 0, 'tokens_out': 0, 'eval_time': 0, 'success': False}

if len(sys.argv) < 2:
    print("Usage: run-kimi.py <task-file>"); sys.exit(1)

task_file = sys.argv[1]
with open(task_file) as f:
    task = json.load(f)

task_id = task.get('id', 'unknown')
desc = task.get('desc', 'No task')

print(f"🚀 Coder Agent (Kimi Cloud): {task_id}")
print(f"   Model: {MODEL}")
print(f"   Task: {desc}")

task['status'] = 'running'
task['started_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
with open(task_file, 'w') as f:
    json.dump(task, f)

result = call_kimi(desc)

if result['success']:
    out_dir = f"{WORKSPACE}/agent-output/{task_id}"
    os.makedirs(out_dir, exist_ok=True)
    out_file = f"{out_dir}/generated{result['extension']}"
    with open(out_file, 'w') as f:
        f.write(result['response'])
    os.chmod(out_file, 0o755)
    
    # Also save to a top-level workspace file for easy access
    with open(f"{WORKSPACE}/last_generated_code{result['extension']}", 'w') as f:
        f.write(result['response'])
    
    # Kimi Code might have a cost - setting 0 for now as it's often in a different pool
    # log_metrics(task_id, result['tokens_in'], result['tokens_out'], result['eval_time'], 0.0)
    
    task.update({'status': 'done', 'completed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 'result': f'Generated {out_file}', 'output_file': out_file})
    
    print(f"✅ Completed!")
    print(f"   Output: {out_file}")
    print(f"   Tokens: {result['tokens_in']} in, {result['tokens_out']} out")
else:
    task.update({'status': 'error', 'error': result['response']})
    print(f"❌ Failed: {result['response']}")

with open(task_file, 'w') as f:
    json.dump(task, f)
