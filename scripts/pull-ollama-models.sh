#!/bin/bash
# Ollama Models Setup for Mac Mini M4
# Pulls all models with Metal GPU optimization

set -e

echo "🤖 Setting up Ollama models on Mac Mini M4..."
echo "📥 This will download ~20GB of models with Metal optimization"
echo ""

# Essential models (must have)
echo "📦 Pulling essential models..."
ollama pull nomic-embed-text
echo "  ✅ nomic-embed-text (for GBrain)"

ollama pull mannix/qwen2.5-coder:0.5b-iq4_xs
echo "  ✅ qwen2.5-coder:0.5b (fast, small)"

# Medium models
echo ""
echo "📦 Pulling medium models..."
ollama pull tinydolphin
echo "  ✅ tinydolphin (smart router)"

ollama pull phi3:mini
echo "  ✅ phi3:mini (Microsoft)"

ollama pull smollm2
echo "  ✅ smollm2 (HuggingFace)"

ollama pull qwen35-4b-text
echo "  ✅ qwen35-4b-text"

ollama pull hf.co/prism-ml/Bonsai-8B-gguf
echo "  ✅ Bonsai-8B-gguf"

# Large models (optional - takes time)
echo ""
echo "📦 Pulling large models..."
ollama pull phi3.5
echo "  ✅ phi3.5 (Microsoft)"

ollama pull mannix/qwen2.5-coder:14b-iq4_xs
echo "  ✅ qwen2.5-coder:14b (coding beast)"

# Gemma 4 (new - for Mac Mini M4 testing)
echo ""
echo "📦 Pulling Gemma 4 (Google)..."
ollama pull gemma:4b
echo "  ✅ gemma:4b (Google)"
ollama pull gemma:2b
echo "  ✅ gemma:2b (Google)"

echo ""
echo "========================================="
echo "  ✅ ALL models pulled successfully!"
echo "========================================="
echo ""
echo "Models installed:"
echo "  • nomic-embed-text (GBrain embeddings)"
echo "  • mannix/qwen2.5-coder:0.5b-iq4_xs (fast coding)"
echo "  • mannix/qwen2.5-coder:14b-iq4_xs (power coding)"
echo "  • phi3:mini (Microsoft)"
echo "  • phi3.5 (Microsoft)"
echo "  • tinydolphin (smart router)"
echo "  • smollm2 (HuggingFace)"
echo "  • qwen35-4b-text"
echo "  • Bonsai-8B-gguf"
echo "  • gemma:4b (Google - NEW!)"
echo "  • gemma:2b (Google)"
echo ""
echo "To test:"
echo "  ollama run mannix/qwen2.5-coder:0.5b-iq4_xs"
echo "  ollama run mannix/qwen2.5-coder:14b-iq4_xs"
echo ""
ollama list