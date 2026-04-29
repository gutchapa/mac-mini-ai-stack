#!/usr/bin/env python3
"""
model-compare.py - Benchmark Kimi vs DeepSeek V4 Flash
Metrics: Speed, tokens, cost, quality
"""

import os
import sys
import time
import json
import urllib.request
import argparse
from datetime import datetime

RESULTS_FILE = os.path.expanduser("~/.openclaw/logs/model-compare.jsonl")

TEST_TASKS = {
    "coding": {
        "prompt": "Write a Python function to sort a list of dictionaries by a key, with error handling for missing keys.",
        "criteria": ["Correctness", "Error handling", "Code quality"]
    },
    "creative": {
        "prompt": "Write an Instagram caption for a school cooking class photo showing kids making dosas. Max 2 sentences, warm tone.",
        "criteria": ["Creativity", "Tone match", "Length"]
    },
    "reasoning": {
        "prompt": "A school has 3 buses. Each bus holds 40 students. If 95 students need transport and each bus makes 2 trips, can all students be transported? Show reasoning.",
        "criteria": ["Logic correctness", "Step-by-step", "Final answer"]
    },
    "summarization": {
        "prompt": "Summarize this in 2 sentences: DeepSeek V4 is a new AI model with 1.6T parameters, supporting 1M token context. It uses Mixture of Experts with only 49B active parameters per query. Released April 2026 under MIT license.",
        "criteria": ["Accuracy", "Brevity", "Key points"]
    }
}

def api_post(url, headers, data, timeout=120):
    """Generic API POST helper."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def run_kimi(prompt, timeout=120):
    """Run prompt through Kimi API."""
    start = time.time()
    try:
        api_key = os.environ.get("KIMI_API_KEY", "")
        if not api_key:
            return error_result("kimi/kimi-code", "KIMI_API_KEY not set")
        
        # Kimi uses Anthropic-style messages API
        result = api_post(
            "https://api.kimi.com/coding/v1/messages",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            data={
                "model": "kimi-code",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=timeout
        )
        
        elapsed = time.time() - start
        
        # Anthropic-style response
        if "content" in result and len(result["content"]) > 0:
            response = result["content"][0].get("text", "")
        else:
            response = str(result)
        
        usage = result.get("usage", {})
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        
        return {
            "model": "kimi/kimi-code",
            "response": response,
            "time_seconds": round(elapsed, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": 0.0,
            "success": len(response) > 20
        }
    except Exception as e:
        return error_result("kimi/kimi-code", str(e)[:100])

def run_deepseek_flash(prompt, timeout=60):
    """Run prompt through DeepSeek V4 Flash via OpenRouter."""
    start = time.time()
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return error_result("deepseek-v4-flash", "OPENROUTER_API_KEY not set")
        
        result = api_post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data={
                "model": "deepseek/deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000
            },
            timeout=timeout
        )
        
        elapsed = time.time() - start
        
        # DeepSeek V4 Flash may return content OR reasoning
        message = result["choices"][0]["message"]
        if message.get("content"):
            response = message["content"]
        elif message.get("reasoning"):
            response = message["reasoning"]
        else:
            response = str(message)
            
        # Include reasoning if present alongside content
        if message.get("reasoning") and message.get("content"):
            response = message["reasoning"] + "\n\n" + message["content"]
            
        usage = result.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        
        # Cost: $0.14/M input, $0.28/M output
        cost = (tokens_in * 0.14 / 1_000_000) + (tokens_out * 0.28 / 1_000_000)
        
        return {
            "model": "deepseek-v4-flash",
            "response": response,
            "time_seconds": round(elapsed, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 6),
            "success": len(response) > 20
        }
    except Exception as e:
        return error_result("deepseek-v4-flash", str(e)[:100])

def error_result(model, error_msg):
    return {
        "model": model,
        "response": f"ERROR: {error_msg}",
        "time_seconds": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "success": False
    }

def run_comparison(tasks_to_run):
    """Run comparison for specified tasks."""
    results = []
    timestamp = datetime.now().isoformat()
    
    for task_name in tasks_to_run:
        if task_name not in TEST_TASKS:
            print(f"⚠️ Unknown task: {task_name}")
            continue
        
        task = TEST_TASKS[task_name]
        prompt = task["prompt"]
        
        print(f"\n{'='*60}")
        print(f"TASK: {task_name.upper()}")
        print(f"Prompt: {prompt[:80]}...")
        print(f"{'='*60}")
        
        # Run Kimi
        print("\n🔄 Kimi (current model)...")
        kimi_result = run_kimi(prompt)
        print(f"  ⏱️  {kimi_result['time_seconds']}s | "
              f"📝 {kimi_result['tokens_in'] + kimi_result['tokens_out']} tokens | "
              f"💰 ${kimi_result['cost_usd']:.6f}")
        
        # Run DeepSeek
        print("\n🔄 DeepSeek V4 Flash (API)...")
        ds_result = run_deepseek_flash(prompt)
        print(f"  ⏱️  {ds_result['time_seconds']}s | "
              f"📝 {ds_result['tokens_in'] + ds_result['tokens_out']} tokens | "
              f"💰 ${ds_result['cost_usd']:.6f}")
        
        # Store result
        comparison = {
            "timestamp": timestamp,
            "task": task_name,
            "prompt": prompt,
            "kimi": kimi_result,
            "deepseek_v4_flash": ds_result,
            "winner_speed": "kimi" if kimi_result["time_seconds"] < ds_result["time_seconds"] else "deepseek",
            "winner_tokens": "kimi" if (kimi_result["tokens_in"] + kimi_result["tokens_out"]) < (ds_result["tokens_in"] + ds_result["tokens_out"]) else "deepseek",
            "winner_cost": "kimi"
        }
        
        results.append(comparison)
        
        # Print responses
        resp_kimi = kimi_result["response"] or ""
        resp_ds = ds_result["response"] or ""
        print(f"\n📝 Kimi Response ({len(resp_kimi)} chars):")
        print(f"   {resp_kimi[:200]}{'...' if len(resp_kimi) > 200 else ''}")
        
        print(f"\n📝 DeepSeek Response ({len(resp_ds)} chars):")
        print(f"   {resp_ds[:200]}{'...' if len(resp_ds) > 200 else ''}")
    
    return results

def print_summary(results):
    """Print comparison summary."""
    print("\n" + "="*60)
    print("COMPARISON SUMMARY: Kimi vs DeepSeek V4 Flash")
    print("="*60)
    
    kimi_wins_speed = sum(1 for r in results if r["winner_speed"] == "kimi")
    ds_wins_speed = sum(1 for r in results if r["winner_speed"] == "deepseek")
    
    total_kimi_time = sum(r["kimi"]["time_seconds"] for r in results)
    total_ds_time = sum(r["deepseek_v4_flash"]["time_seconds"] for r in results)
    
    total_ds_cost = sum(r["deepseek_v4_flash"]["cost_usd"] for r in results)
    
    print(f"\n⏱️  SPEED:")
    print(f"   Kimi wins: {kimi_wins_speed}/{len(results)} tasks")
    print(f"   DeepSeek wins: {ds_wins_speed}/{len(results)} tasks")
    print(f"   Kimi total time: {total_kimi_time:.1f}s")
    print(f"   DeepSeek total time: {total_ds_time:.1f}s")
    if total_kimi_time < total_ds_time:
        print(f"   ✅ Speed advantage: Kimi ({abs(total_kimi_time - total_ds_time):.1f}s faster)")
    else:
        print(f"   ✅ Speed advantage: DeepSeek ({abs(total_kimi_time - total_ds_time):.1f}s faster)")
    
    print(f"\n💰 COST:")
    print(f"   Kimi: $0.00 (quota-based)")
    print(f"   DeepSeek: ${total_ds_cost:.6f} total")
    print(f"   Cost per query: ~${total_ds_cost/len(results):.6f}")
    
    print(f"\n📝 OUTPUT SIZE:")
    kimi_total_chars = sum(len(r["kimi"]["response"] or "") for r in results)
    ds_total_chars = sum(len(r["deepseek_v4_flash"]["response"] or "") for r in results)
    print(f"   Kimi: {kimi_total_chars} chars total")
    print(f"   DeepSeek: {ds_total_chars} chars total")
    
    print(f"\n✅ SUCCESS RATE:")
    kimi_success = sum(1 for r in results if r["kimi"]["success"])
    ds_success = sum(1 for r in results if r["deepseek_v4_flash"]["success"])
    print(f"   Kimi: {kimi_success}/{len(results)}")
    print(f"   DeepSeek: {ds_success}/{len(results)}")
    
    print(f"\n💡 VERDICT:")
    if total_kimi_time < total_ds_time and kimi_success >= ds_success:
        print("   Kimi wins on speed and reliability. Keep current setup.")
    elif ds_success > kimi_success or (total_ds_time < total_kimi_time and ds_success == kimi_success):
        print("   DeepSeek wins on speed/reliability. Consider switching.")
    else:
        print("   Trade-off: Kimi for free quota, DeepSeek for speed/consistency.")
    
    print(f"\n   At 100 queries/day:")
    print(f"   - Kimi: $0.00 (until quota runs out)")
    print(f"   - DeepSeek: ~${total_ds_cost/len(results)*100:.2f}/day")
    print(f"   - DeepSeek monthly: ~${total_ds_cost/len(results)*100*30:.2f}")
    
    print(f"\n⚠️  KIMI RISKS:")
    print(f"   - Server outages (happened today)")
    print(f"   - Monthly quota limits")
    print(f"   - Session interruptions")
    print(f"\n⚠️  DEEPSEEK RISKS:")
    print(f"   - API dependency (needs internet)")
    print(f"   - Small cost ($0.44/month)")
    print(f"   - New model, potential instability")

def save_results(results):
    """Save results to log file."""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"\n💾 Results saved to: {RESULTS_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Compare Kimi vs DeepSeek V4 Flash")
    parser.add_argument("--tasks", "-t", default="coding,creative,reasoning,summarization",
                       help="Comma-separated tasks to run")
    parser.add_argument("--save", "-s", action="store_true", help="Save results")
    
    args = parser.parse_args()
    tasks = [t.strip() for t in args.tasks.split(",")]
    
    print("🧪 Model Comparison: Kimi (current) vs DeepSeek V4 Flash (API)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🖥️  Host: Mac Mini M4 (16GB)")
    
    results = run_comparison(tasks)
    print_summary(results)
    
    if args.save:
        save_results(results)

if __name__ == "__main__":
    main()
