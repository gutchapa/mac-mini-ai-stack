#!/usr/bin/env python3
"""GBrain Memory Adapter for CrewAI - Uses local GBrain instead of default memory"""
import subprocess
import os

class GBrainMemory:
    def __init__(self):
        self.workspace = os.environ.get('WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
        self.gbrain_repo = os.environ.get('GBRAIN_REPO', os.path.expanduser('~/gbrain-repo'))
    
    def add(self, text, metadata=None):
        """Add memory to GBrain"""
        # Create temporary file and import
        temp_file = f"{self.workspace}/temp_memory.txt"
        with open(temp_file, 'w') as f:
            f.write(text)
        
        subprocess.run(
            ['bun', 'run', 'src/cli.ts', 'import', temp_file],
            cwd=self.gbrain_repo,
            capture_output=True
        )
    
    def search(self, query, limit=5):
        """Search GBrain for relevant memories"""
        result = subprocess.run(
            ['bun', 'run', 'src/cli.ts', 'query', query],
            cwd=self.gbrain_repo,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def get_context(self, query):
        """Get context for LLM prompt"""
        results = self.search(query)
        return f"Context from GBrain:\n{results}\n\n"
