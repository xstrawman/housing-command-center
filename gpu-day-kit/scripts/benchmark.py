#!/usr/bin/env python3
"""Benchmark LLM endpoints using Housing Command Center agent prompts."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

KIT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS = KIT / "prompts" / "benchmark.json"
DEFAULT_OUT = KIT / "exports" / "benchmark_results.json"


@dataclass
class CaseResult:
    id: str
    agent: str
    ok: bool
    latency_s: float
    output_chars: int
    output_tokens_est: int
    json_valid: bool | None
    error: str | None
    output_preview: str


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def chat(base_url: str, model: str, prompt: str, *, max_tokens: int, temperature: float, system_prefix: str) -> tuple[str, float]:
    started = time.perf_counter()
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": f"{system_prefix}{prompt}"}],
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        },
        timeout=300,
    )
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "").strip()
    # Strip Qwen thinking blocks
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content, time.perf_counter() - started


def try_parse_json(text: str) -> bool:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        # Try to find first JSON object
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                json.loads(match.group(0))
                return True
            except json.JSONDecodeError:
                return False
        return False


def run_benchmark(
    base_url: str,
    model: str,
    prompts_path: Path,
    *,
    label: str,
    runs: int = 1,
) -> dict:
    spec = json.loads(prompts_path.read_text(encoding="utf-8"))
    system_prefix = spec.get("system_prefix", "")
    results: list[CaseResult] = []

    for case in spec["cases"]:
        for run_idx in range(runs):
            case_id = case["id"] if runs == 1 else f"{case['id']}_run{run_idx + 1}"
            try:
                output, latency = chat(
                    base_url,
                    model,
                    case["prompt"],
                    max_tokens=case.get("max_tokens", 400),
                    temperature=case.get("temperature", 0.3),
                    system_prefix=system_prefix,
                )
                json_valid = None
                if case["agent"] == "parser":
                    json_valid = try_parse_json(output)
                ok = bool(output) and not output.startswith("<think>")
                if json_valid is False:
                    ok = False
                results.append(
                    CaseResult(
                        id=case_id,
                        agent=case["agent"],
                        ok=ok,
                        latency_s=round(latency, 3),
                        output_chars=len(output),
                        output_tokens_est=estimate_tokens(output),
                        json_valid=json_valid,
                        error=None,
                        output_preview=output[:400],
                    )
                )
            except Exception as exc:
                results.append(
                    CaseResult(
                        id=case_id,
                        agent=case["agent"],
                        ok=False,
                        latency_s=0.0,
                        output_chars=0,
                        output_tokens_est=0,
                        json_valid=None,
                        error=str(exc),
                        output_preview="",
                    )
                )

    latencies = [r.latency_s for r in results if r.ok and r.latency_s > 0]
    tokens = [r.output_tokens_est for r in results if r.ok]
    summary = {
        "label": label,
        "base_url": base_url,
        "model": model,
        "cases": len(spec["cases"]),
        "runs": runs,
        "total_requests": len(results),
        "successes": sum(1 for r in results if r.ok),
        "failures": sum(1 for r in results if not r.ok),
        "latency_s": {
            "mean": round(statistics.mean(latencies), 3) if latencies else None,
            "p50": round(statistics.median(latencies), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "throughput_tok_per_s_est": (
            round(sum(tokens) / sum(latencies), 1) if latencies and sum(latencies) > 0 else None
        ),
        "parser_json_valid_rate": (
            round(
                sum(1 for r in results if r.json_valid is True)
                / max(1, sum(1 for r in results if r.json_valid is not None)),
                2,
            )
        ),
        "results": [asdict(r) for r in results],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="Qwen3-8B-int4-cw")
    parser.add_argument("--label", default="npu")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--compare", action="store_true", help="Also benchmark HCC_GPU_LLM_* env vars")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    import os

    reports = [
        run_benchmark(args.url, args.model, args.prompts, label=args.label, runs=args.runs),
    ]

    if args.compare:
        gpu_url = os.environ.get("HCC_GPU_LLM_URL", "http://127.0.0.1:11434")
        gpu_model = os.environ.get("HCC_GPU_LLM_MODEL", "qwen3:8b")
        reports.append(
            run_benchmark(gpu_url, gpu_model, args.prompts, label="gpu", runs=args.runs)
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"reports": reports, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for report in reports:
        print(
            f"[{report['label']}] {report['successes']}/{report['total_requests']} ok | "
            f"latency mean={report['latency_s']['mean']}s | "
            f"tok/s≈{report['throughput_tok_per_s_est']}"
        )
    print(f"Results → {args.out}")
    return 0 if all(r["failures"] == 0 for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())