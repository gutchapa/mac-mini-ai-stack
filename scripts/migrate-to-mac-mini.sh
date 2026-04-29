#!/bin/bash
# migrate-to-mac-mini.sh - Dell WSL → Mac Mini M4 Migration
# Updated: April 2025 with SOUL-EL, Dynamic Deployment, Browser Components

# ============================================================================
# MAC MINI M4 MIGRATION GUIDE
# ============================================================================
# HARDWARE DIFFERENCES:
# - Dell: x86_64, 16GB RAM, WSL2
# - Mac Mini M4: ARM64 (Apple Silicon), 16GB unified RAM, macOS
#
# NEW COMPONENTS TO MIGRATE:
# - SOUL Enforcement Layer (soul-enforcer.sh)
# - Dynamic Deployment (ollama_llm.py with auto-file-materialization)
# - Enhanced Coder Agent (run-kimi.py with multi-language support)
# - Browser Components (simple-browser/, simple-browser-ts/)
# - Code Burn fixes (improved observability, verification receipts)
# ============================================================================

echo "=========================================="
echo "Mac Mini M4 Migration Script"
echo "Dell WSL2 → Mac Mini M4 (Apple Silicon)"
echo "=========================================="
echo ""

# Step 0: Pre-Migration Checklist
echo "Step 0: Pre-Migration Checklist"
echo "------------------------------------------"
cat << 'CHECKLIST'
□ Mac Mini arrived and unboxed
□ Initial macOS setup complete (Apple ID, etc.)
□ Homebrew installed: /bin/bash -c "$(curl -fsSL ...)"
□ SSH access configured (or physical access)
□ GitHub credentials ready
□ This script copied to Mac Mini

CHECKLIST

echo ""
echo "Step 1: Install Core Dependencies"
echo "------------------------------------------"
cat << 'DEPS'
# On Mac Mini Terminal:

# Install Homebrew (if not done)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Core tools
brew install git node python@3.12 python@3.11 ollama tmux tree jq htop

# Setup Python aliases (macOS uses python3)
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc

# Install Node.js package managers
npm install -g pnpm bun

DEPS

echo ""
echo "Step 2: Setup Ollama with Metal GPU"
echo "------------------------------------------"
cat << 'OLLAMA'
# Ollama auto-starts with brew service
brew services start ollama

# Pull models (prioritize based on your usage)
ollama pull phi3:mini          # 2.2GB - Fast, reliable baseline
ollama pull tinydolphin        # 636MB - Ultra-fast for simple tasks  
ollama pull qwen2.5-coder:0.5b # 349MB - Coding tasks
ollama pull gemma3:4b          # 4B - Better quality responses
ollama pull qwen:14b           # 14B - Was OOM on Dell, should work on Mac!
ollama pull deepseek-r1:8b     # 8B reasoning model

# Test with Metal acceleration
ollama run phi3:mini "System check from Mac Mini M4"

# Expected: First load ~20-30s, then faster
OLLAMA

echo ""
echo "Step 3: Clone and Setup OpenClaw Workspace"
echo "------------------------------------------"
cat << 'WORKSPACE'
# Create workspace directory
mkdir -p ~/openclaw && cd ~/openclaw

# Clone your repo
git clone https://github.com/gutchapa/dell-claw-mini.git workspace
cd workspace

# Switch to the updated branch
git checkout dell-mini-pc-setup-v3

# CRITICAL: Update hardcoded paths
# Dell: /home/dell/.openclaw/workspace
# Mac:  /Users/$USER/openclaw/workspace

WORKSPACE

echo ""
echo "Step 4: Update Hardcoded Paths (CRITICAL!)"
echo "------------------------------------------"
cat << 'PATHS'
# Files that need path updates:
# - soul-enforcer.sh (VIOLATION_LOG path)
# - openclaw-adapters/adapters/ollama_llm.py (self.workspace)
# - subagents/coder/run-kimi.py (WORKSPACE constant)
# - Any custom scripts with /home/dell paths

# Quick fix using sed:
cd ~/openclaw/workspace

# Backup first
cp soul-enforcer.sh soul-enforcer.sh.bak
cp openclaw-adapters/adapters/ollama_llm.py ollama_llm.py.bak
cp subagents/coder/run-kimi.py run-kimi.py.bak

# Replace paths (use actual username, not $USER)
sed -i '' 's|/home/dell/.openclaw/workspace|/Users/YOUR_USERNAME/openclaw/workspace|g' soul-enforcer.sh
sed -i '' 's|/home/dell/.openclaw/workspace|/Users/YOUR_USERNAME/openclaw/workspace|g' openclaw-adapters/adapters/ollama_llm.py
sed -i '' 's|/home/dell/.openclaw/workspace|/Users/YOUR_USERNAME/openclaw/workspace|g' subagents/coder/run-kimi.py

# Or use environment variable approach (better!):
# Change hardcoded paths to use $WORKSPACE env var

PATHS

echo ""
echo "Step 5: Setup Environment Variables"
echo "------------------------------------------"
cat << 'ENV'
# Add to ~/.zshrc (or ~/.bash_profile):

# OpenClaw workspace
export WORKSPACE="$HOME/openclaw/workspace"

# API Keys (from your existing setup)
export KIMI_API_KEY="sk-kimi-l0Ju2tcVDDPnhM1YwyYls2k3I4n8RVhnNNIs32EfDmLSmqeGLoSgXxHuxshjWNqo"

# Path for global npm packages
export PATH="$HOME/.npm-global/bin:$PATH"

# Ollama host (if needed)
export OLLAMA_HOST="http://localhost:11434"

# Reload shell
source ~/.zshrc

ENV

echo ""
echo "Step 6: Install OpenClaw CLI"
echo "------------------------------------------"
cat << 'CLI'
# Install OpenClaw globally
npm install -g openclaw

# Verify installation
openclaw --version
openclaw status

# If you get permission errors:
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH

CLI

echo ""
echo "Step 7: Test All Components"
echo "------------------------------------------"
cat << 'TEST'
# Run these tests to verify everything works:

cd $WORKSPACE

# Test 1: SOUL Enforcement Layer
bash soul-enforcer.sh check "I will create a Python script"
# Expected: VIOLATION detected (not using CrewAI)

bash soul-enforcer.sh check "Using CrewAI for orchestration"
# Expected: PASS

# Test 2: Coder Agent (Kimi Cloud)
echo '{"id": "test-mac", "desc": "Write hello world in Python"}' > /tmp/test.json
python3 subagents/coder/run-kimi.py /tmp/test.json
ls -la agent-output/test-mac/

# Test 3: Ollama Adapter
python3 -c "
from openclaw-adapters.adapters.ollama_llm import OllamaLLM
llm = OllamaLLM('phi3:mini')
result = llm.call('Hello from Mac Mini')
print(result)
"

# Test 4: Git sync
git status
git log --oneline -3

TEST

echo ""
echo "Step 8: Optional - Copy Memory Files"
echo "------------------------------------------"
cat << 'MEMORY'
# For continuity, copy memory files from Dell:

# From Mac Mini:
scp -r dell-user@dell-ip:/home/dell/.openclaw/workspace/memory ~/openclaw/workspace/

# Or if using USB:
cp -r /Volumes/USB/memory ~/openclaw/workspace/

# Files to preserve:
# - memory/2025-04-*.md (daily logs)
# - memory/soul-violations.md (audit trail)
# - .route_cache.json (if you have travel routes)

MEMORY

echo ""
echo "Step 9: llama.cpp with Metal (Optional)"
echo "------------------------------------------"
cat << 'LLAMACPP'
# If using llama.cpp directly (not just Ollama):

cd ~
git clone --depth 1 https://github.com/ggerganov/llama.cpp.git llama.cpp-mac
cd llama.cpp-mac
mkdir build && cd build

# Build with Metal GPU support
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_METAL=ON \
  -DLLAMA_METAL_EMBED_LIBRARY=ON \
  -DCMAKE_SYSTEM_PROCESSOR=arm64 \
  -DCMAKE_OSX_ARCHITECTURES=arm64

cmake --build . --config Release -j8

# Test with a model
./bin/llama-cli \
  -m ~/models/phi3-mini-q4.gguf \
  -p "Hello from Mac Mini" -n 50 \
  -ngl 99  # Metal GPU layers

# Expected: 10+ tok/s (vs 5-6 on Dell)

LLAMACPP

echo ""
echo "=========================================="
echo "NEW COMPONENTS REFERENCE"
echo "=========================================="
echo ""
echo "🔒 SOUL-EL (SOUL Enforcement Layer):"
echo "   - File: soul-enforcer.sh"
echo "   - Purpose: Real-time compliance checking"
echo "   - Checks: CrewAI orchestration, completeness, delegation"
echo "   - Log: memory/soul-violations.md"
echo ""
echo "📦 Dynamic Deployment:"
echo "   - File: openclaw-adapters/adapters/ollama_llm.py"
echo "   - Feature: Auto-materializes files from prompt paths"
echo "   - Example: 'Create simple-browser/App.tsx' → file created at that path"
echo ""
echo "🚀 Enhanced Coder Agent:"
echo "   - File: subagents/coder/run-kimi.py"
echo "   - Features: Multi-language support, error handling, verification"
echo "   - Supports: Python, TypeScript, JSX, HTML"
echo ""
echo "🌐 Browser Components:"
echo "   - simple-browser/: React Native mobile browser"
echo "   - simple-browser-ts/: Vite+React desktop browser"
echo "   - system prompts for AI integration included"
echo ""
echo "✅ Code Burn Improvements:"
echo "   - Better token tracking"
echo "   - Verification receipts (ls -l + head)"
echo "   - Proper extension detection"
echo ""
echo "=========================================="
echo "TROUBLESHOOTING"
echo "=========================================="
echo ""
echo "❌ 'ollama' command not found"
echo "   → brew install ollama && brew services start ollama"
echo ""
echo "❌ Path errors in scripts"
echo "   → Update hardcoded /home/dell → /Users/\$USER"
echo ""
echo "❌ Python module not found"
echo "   → Use 'python3' not 'python' on macOS"
echo ""
echo "❌ Kimi API 401 error"
echo "   → Check KIMI_API_KEY is exported correctly"
echo ""
echo "❌ Permission denied on npm global"
echo "   → Use ~/.npm-global instead of /usr/local"
echo ""
echo "=========================================="
echo "PERFORMANCE EXPECTATIONS"
echo "=========================================="
echo ""
echo "| Task           | Dell (WSL2)   | Mac Mini M4   |"
echo "|----------------|---------------|---------------|"
echo "| phi3:mini      | ~49s first    | ~20-30s       |"
echo "| tinydolphin    | Fast          | Faster        |"
echo "| 14B models     | OOM ❌        | Should work ✅ |"
echo "| Kimi API       | ~3-5s         | ~3-5s (same)  |"
echo "| Code gen       | ~5-10s        | ~3-5s         |"
echo ""
echo "=========================================="
echo "POST-MIGRATION TASKS"
echo "=========================================="
echo ""
echo "□ Test 14B models (qwen:14b, deepseek-r1:14b)"
echo "□ Run benchmarks vs Dell numbers"
echo "□ Update USER.md with Mac Mini specs"
echo "□ Archive Dell setup when Mac stable"
echo "□ Update any hardcoded paths in new scripts"
echo ""
echo "=========================================="
echo "Ready to migrate! Good luck! 🍎🚀"
echo "=========================================="
