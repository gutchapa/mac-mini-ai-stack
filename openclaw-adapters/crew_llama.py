#!/usr/bin/env python3
"""CrewAI with Llama.cpp"""
import sys
sys.path.insert(0, '/home/dell/.openclaw/workspace/openclaw-adapters')

from crewai import Agent, Task, Crew
from adapters.llama_cpp_adapter import LlamaLLM

llm = LlamaLLM(model="phi3-mini")

coder = Agent(
    role="Python Developer",
    goal="Write Python code",
    backstory="Expert Python developer",
    llm=llm,
    allow_delegation=False
)

task = Task(
    description="Write a fibonacci function",
    agent=coder,
    expected_output="Python function"
)

crew = Crew(agents=[coder], tasks=[task], verbose=True)

if __name__ == "__main__":
    print("🚀 CrewAI + Llama.cpp")
    result = crew.kickoff()
    print(result)
