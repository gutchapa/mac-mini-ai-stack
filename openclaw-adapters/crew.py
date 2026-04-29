#!/usr/bin/env python3
"""OpenClaw Crew - CrewAI integration with local stack"""
import os
import sys

# Add adapters to path
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/openclaw-adapters'))

from adapters.ollama_llm import OllamaLLM
from adapters.gbrain_memory import GBrainMemory

class OpenClawCrew:
    """CrewAI crew using our local stack"""
    
    def __init__(self):
        self.workspace = os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
        self.llm = OllamaLLM(model="phi3:mini")
        self.memory = GBrainMemory()
    
    def run_task(self, task_description):
        """Run a task through our local agent"""
        print(f"🎯 Task: {task_description}")
        
        # Get context from GBrain
        context = self.memory.get_context(task_description)
        
        # Build prompt
        prompt = f"{context}\n\nTask: {task_description}\n\nWrite working code:"
        
        # Call local agent
        result = self.llm.call(prompt)
        
        # Store in GBrain
        self.memory.add(f"Task: {task_description}\nResult: {result}")
        
        return result

if __name__ == "__main__":
    crew = OpenClawCrew()
    task = sys.argv[1] if len(sys.argv) > 1 else "Write a hello world function"
    result = crew.run_task(task)
    print("\n✅ Result:")
    print(result)
