#!/usr/bin/env python3
"""LlamaCPP Adapter - CrewAI compatible"""
import subprocess
from crewai import BaseLLM
from typing import Any, Dict, List, Optional, Union

class LlamaLLM(BaseLLM):
    """CrewAI-compatible llama.cpp adapter"""
    
    def __init__(self, model: str = "phi3-mini", temperature: Optional[float] = None, **kwargs):
        super().__init__(model=model, temperature=temperature)
        
        paths = {"phi3-mini": "/home/dell/models/phi3-mini-q3.gguf"}
        self.model_path = paths.get(model, model)
        self.cli = "/home/dell/llama.cpp/build/bin/llama-cli"
    
    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs  # Accept extra CrewAI params
    ) -> str:
        """Call llama.cpp with prompt"""
        
        # Handle messages format
        if isinstance(messages, str):
            prompt = messages
        else:
            # Extract content from messages
            prompt = "\n".join([m.get("content", "") for m in messages])
        
        cmd = [
            self.cli,
            "-m", self.model_path,
            "-p", prompt,
            "-n", "500",  # max tokens
            "--ctx-size", "4096",
            "--threads", "4",
            "--temp", str(self.temperature or 0.7),
            "--no-display-prompt",
            "--log-disable"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr[:200]}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def supports_function_calling(self) -> bool:
        return False
    
    def get_context_window_size(self) -> int:
        return 4096

if __name__ == "__main__":
    llm = LlamaLLM()
    print(llm.call("Hi! How are you?"))
