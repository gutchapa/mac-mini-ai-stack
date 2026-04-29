#!/usr/bin/env python3
"""Ollama LLM Adapter for CrewAI - Routes to local agents"""
import subprocess
import json
import os

class OllamaLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.workspace = os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
    
    def call(self, prompt, **kwargs):
        task_id = f"crewai_{hash(prompt) & 0xFFFFFFFF}"
        task_file = f"{self.workspace}/orchestrator/queue/{task_id}.json"
        os.makedirs(os.path.dirname(task_file), exist_ok=True)
        
        with open(task_file, 'w') as f:
            json.dump({'id': task_id, 'desc': prompt[:200], 'agent': 'coder', 'status': 'queued'}, f)
        
        # Run agent
        agent_script = f"{self.workspace}/subagents/coder/run-kimi.py"
        result = subprocess.run(['python3', agent_script, task_file], capture_output=True, text=True, timeout=120)
        
        # Find the generated file (it could have different extensions now)
        out_dir = f"{self.workspace}/agent-output/{task_id}"
        generated_files = [f for f in os.listdir(out_dir) if f.startswith("generated")] if os.path.exists(out_dir) else []
        
        if generated_files:
            output_file = f"{out_dir}/{generated_files[0]}"
            with open(output_file, 'r') as f:
                content = f.read()
                
                # Dynamic Deployment: Try to find a path in the prompt (e.g. "simple-browser/App.tsx")
                import re
                path_match = re.search(r'([a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]+)', prompt)
                if path_match:
                    target_path = path_match.group(1)
                    # Don't overwrite system files or this script
                    if not any(x in target_path for x in ["ollama_llm.py", "run-kimi.py", "openclaw.json"]):
                        full_target = os.path.join(self.workspace, target_path)
                        os.makedirs(os.path.dirname(full_target), exist_ok=True)
                        with open(full_target, 'w') as tf:
                            tf.write(content)
                        print(f"📦 Materialized: {target_path}")
                
                return content
        
        # If file missing, check result for error message
        if result.returncode != 0:
            return f"Error executing coder agent: {result.stderr}"
        return result.stdout if result.stdout else "No output"
