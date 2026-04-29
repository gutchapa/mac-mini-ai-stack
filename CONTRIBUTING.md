# 🤝 Contributing to Mac Mini AI Stack

Thanks for wanting to contribute! This repo is meant to be a useful, practical resource for anyone running AI on Apple Silicon Macs.

## What We'd Love

- **New adapters** — Ollama adapter for other models (Llama 4, Mistral, DeepSeek local, etc.)
- **Benchmark data** — Run the shootout on M1/M2/M3/M4 Ultra/Max and submit results
- **Bug fixes** — Typos, script errors, edge cases
- **Docs** — Better READMEs, troubleshooting guides
- **Example apps** — More Gemma 4 built apps to showcase
- **Scripts** — New tools for observability, deployment, monitoring

## Guidelines

1. **No secrets** — Never commit API keys, tokens, or credentials
2. **No session history** — This is a public repo, keep conversation data private
3. **Pin your deps** — If you add Python/Node packages, update the lockfiles too
4. **Test on Mac** — This is Apple Silicon specific, make sure it runs on M-series
5. **Keep it practical** — Real-world useful, not just cool demos

## PR Process

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `bash scripts/codeburn.sh` to check for secrets
5. Submit a PR with a clear description

## Running Benchmarks

Want to add your benchmark data?

```bash
# Run the quality shootout on your Mac
python bin/model-cmp.py --model1 gemma4:2b --prompt "Your test prompt"

# Submit results as a PR with format:
# benchmarks/<date>/README.md
# benchmarks/<date>/shootout_<engine>.txt
```

## Questions?

Open a [Discussion](https://github.com/gutchapa/mac-mini-ai-stack/discussions) — happy to help!
