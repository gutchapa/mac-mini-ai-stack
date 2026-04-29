#!/usr/bin/env python3
"""LlamaCPP Adapter - Using Qwen 3.5 4B instead of Phi-3"""
import subprocess
from crewai import BaseLLM
from typing import Any, Dict, List, Optional, Union

class LlamaLLM(BaseLLM):
    """CrewAI-compatible llama.cpp adapter"""
    
    def __init__(self, model: str = "qwen35-4b", temperature: Optional[float] = None, **kwargs):
        super().__init__(model=model, temperature=temperature)
        
        # Use Qwen 3.5 4B - better performance on Dell
        paths = {
            "qwen35-4b": "/home/dell/.ollama/models/blobs/sha256-30be52c4f0e8fc1311693ea36764dbfe9ce4219d7b1f4111b07251511d71f0b7",
            "phi3-mini": "/home/dell/models/phi3-mini-q3.gguf"
        }
        self.model_path = paths.get(model, model)
        self.cli = "/home/dell/llama.cpp/build/bin/llama-cli"
    
    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Call llama.cpp with prompt"""
        
        if isinstance(messages, str):
            prompt = messages
        else:
            prompt = "\n".join([m.get("content", "") for m in messages])
        
        # Use qwen chat format
        formatted_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        
        cmd = [
            self.cli,
            "-m", self.model_path,
            "-p", formatted_prompt,
            "-n", "500",
            "--ctx-size", "4096",
            "--threads", "4",
            "--temp", str(self.temperature or 0.7),
            "--no-display-prompt",
            "--log-disable"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = result.stdout.strip()
            # Clean up chat format markers
            output = output.replace("<|im_start|>", "").replace("<|im_end|>", "").replace("assistant", "").strip()
            return output if result.returncode == 0 else f"Error: {result.stderr[:200]}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def supports_function_calling(self) -> bool:
        return False
    
    def get_context_window_size(self) -> int:
        return 4096

if __name__ == "__main__":
    llm = LlamaLLM(model="qwen35-4b")
    print("Testing Qwen 3.5 4B:")
    print(llm.call("Write a simple hello world function in Python"))
