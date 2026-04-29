#!/bin/bash
# 🚀 Mac Mini AI Stack — One-command setup
# Run: bash scripts/setup.sh

set -e

echo "🍎 Mac Mini AI Stack Setup"
echo "========================="
echo ""

# Check Apple Silicon
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo "⚠️  This stack is optimized for Apple Silicon Macs (M-series)."
    echo "   You're running on $ARCH. Some features may not work."
fi

# Install Homebrew if missing
if ! command -v brew &>/dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Ollama
if ! command -v ollama &>/dev/null; then
    echo "📦 Installing Ollama..."
    brew install ollama
fi

# Start Ollama
echo "🚀 Starting Ollama..."
ollama serve &
sleep 2

# Pull Gemma 4
echo "📥 Pulling Gemma 4 E4B..."
ollama pull gemma4:2b

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo ""
echo "Test it:"
echo "  ollama run gemma4:2b 'Hello, world!'"
echo ""
echo "Run a task:"
echo "  python bin/crewai-task.py 'your task'"
echo ""
echo "Benchmark:"
echo "  python bin/model-cmp.py --model1 gemma4:2b --prompt 'test'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"