# Gemma 4 Inference Engine Shootout — 2026-04-28

## Hardware
- Mac Mini M4 (16 GB RAM, 256 GB SSD)
- macOS, Metal GPU backend

## Models Tested

| Engine | Model Variant | Quant | Size | Speed | RAM |
|--------|--------------|-------|-----:|:----:|:---:|
| Ollama | Gemma 4 E4B | Q4_K_M | 4.6 GB | 27 t/s | 6-8 GB |
| MLX-VLM | Gemma 4 E4B (converted) | 4bit | 6.4 GB | 21 t/s | 6.9 GB |
| MLX-VLM | Gemma 4 E2B (community) | 4bit | 3.4 GB | 60 t/s | 3.6 GB |

## Verdict
**Ollama wins for daily use.** Same Gemma 4 E4B model, identical output quality, 120x faster generation than MLX-VLM for the same E4B weights. MLX is useful for the E2B variant when speed or RAM efficiency is critical.

## Quality Test
Task: "Create a standalone HTML School Fee Receipt Generator" (8 requirements)
- Ollama: 15,506 chars in 1.5s ✅ All 8 requirements met
- MLX E4B: 16,036 chars in 186s ✅ All 8 requirements met (most verbose)
- MLX E2B: 12,158 chars in 47.5s ⚠️ Functional, missing some polish

## Key Learnings
1. Ollama = llama.cpp under the hood (GGUF + Metal). No need to test them separately.
2. MLX-LM 0.31.3 lacks shared KV layer support for Gemma 4 (needs mlx-vlm 0.4.4)
3. Community MLX models from LM Studio have format mismatches — use official HF conversion
4. Gemma 4 output quality is identical across all engines; only speed and RAM differ
