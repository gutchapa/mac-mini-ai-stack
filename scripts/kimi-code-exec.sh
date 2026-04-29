#!/bin/bash
# kimi-code-exec.sh - Use Kimi Cloud instead of xAI/Grok for code execution
# Wrapper to replace code_execution tool with Kimi API

API_KEY="${KIMI_API_KEY:-sk-kimi-l0Ju2tcVDDPnhM1YwyYls2k3I4n8RVhnNNIs32EfDmLSmqeGLoSgXxHuxshjWNqo}"
API_URL="https://api.kimi.com/coding/v1/messages"

# Read the task from stdin or argument
TASK="${1:-$(cat)}"

# Call Kimi API
response=$(curl -s -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"kimi-code\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"You are a Python expert. Execute the following task and return only the result.\"},
      {\"role\": \"user\", \"content\": \"$TASK\"}
    ],
    \"max_tokens\": 4096
  }" 2>/dev/null)

# Extract content from response
echo "$response" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4

# Log usage
mkdir -p "$WORKSPACE/observability/metrics"
echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"tool\":\"kimi-code-exec\",\"task\":\"${TASK:0:50}\",\"provider\":\"kimi-cloud\"}" >> "$WORKSPACE/observability/metrics/kimi-exec.jsonl"
