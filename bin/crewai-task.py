#!/usr/bin/env python3
"""CrewAI Task Runner - Routes tasks through the orchestration layer"""
import sys
import os
import json
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE / "openclaw-adapters"))

from adapters.ollama_llm import OllamaLLM
from adapters.gbrain_memory import GBrainMemory


class CrewAITaskRunner:
    def __init__(self, model="gemma4:e4b-q4"):
        self.workspace = str(WORKSPACE)
        self.llm = OllamaLLM(model=model)
        self.memory = GBrainMemory()
        self.model = model

    def run(self, task_type, task_desc, context_file=None):
        """Run a task through the CrewAI pipeline"""
        print(f"🎯 CrewAI Task [{task_type}]: {task_desc[:80]}...")
        
        # Load context if provided
        context = ""
        if context_file and Path(context_file).exists():
            context = Path(context_file).read_text()
            print(f"   📄 Loaded context: {len(context)} chars")
        
        # Build prompt
        prompt = f"{context}\n\nTask ({task_type}): {task_desc}\n\nOutput the code only."
        
        # Run through LLM
        result = self.llm.call(prompt)
        
        # Store in GBrain
        self.memory.add(json.dumps({
            "type": task_type,
            "desc": task_desc,
            "result_len": len(result)
        }))
        
        return result

    def code_review(self, file_path):
        """Run the code reviewer agent"""
        from subprocess import run
        result = run(["bash", str(WORKSPACE / "subagents/reviewer/review.sh")], 
                     capture_output=True, text=True, timeout=30)
        return result.stdout


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: crewai-task.py <task_type> <description> [context_file]")
        print("  task_type: code | research | plan | review")
        sys.exit(1)
    
    task_type = sys.argv[1]
    task_desc = sys.argv[2]
    context_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    runner = CrewAITaskRunner()
    if task_type == "review":
        print(runner.code_review(task_desc))
    else:
        result = runner.run(task_type, task_desc, context_file)
        print(f"\n✅ Result ({len(result)} chars):")
        # If it looks like code, wrap in code block
        if result.strip().startswith("def") or result.strip().startswith("<"):
            print("```")
            print(result)
            print("```")
        else:
            print(result)
