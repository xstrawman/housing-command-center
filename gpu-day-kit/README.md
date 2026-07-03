# GPU Day Kit

Everything you need for a rented GPU session (96GB VRAM) to improve Housing Command Center agents.

## Quick start (do this now — no GPU)

```bash
cd ~/housing-command-center
hcc gpu-day prep
```

This exports your database, pre-fills **218 outreach drafts**, and builds **2000 synthetic email-reply prompts** for batch generation.

## GPU rental day — recommended order

| Step | Time est. | Command |
|------|-----------|---------|
| 1. Heretic abliterate Qwen3-8B | ~30–60 min | `hcc gpu-day heretic` |
| 2. Export OpenVINO INT4 | ~20–40 min | `hcc gpu-day openvino` |
| 3. Deploy to NoLlama NPU | ~2 min | `hcc gpu-day deploy` |
| 4. Benchmark before/after | ~5 min | `hcc gpu-day benchmark --compare` |
| 5. Batch synthetic data | ~1–2 hr | see below |
| 6. LoRA fine-tune (optional) | ~2–4 hr | `lora/housing_case_manager.yaml` |

Copy `config.env.example` → `config.env` and set paths before step 1.

## What each piece does

### Export bundle (`export`)
Snapshots `housing.db`, 218 focus properties, outreach templates, focus filter, prompts, and schemas into `exports/<timestamp>/`.

### Benchmark (`benchmark`)
Runs the same prompts your agents use:
- Briefing polish (Strategist)
- Outreach tighten (Outreach Drafter)
- Waitlist JSON parse (future Intel Parser)
- Task prioritization

Compare NPU (NoLlama `:11435`) vs GPU (Ollama `:11434`):

```bash
hcc gpu-day benchmark --compare
```

### Heretic → OpenVINO → NoLlama pipeline

```
Qwen/Qwen3-8B  →  Heretic  →  ~/models/Qwen3-8B-heretic
                              ↓ optimum-cli export openvino
               ~/models/Qwen3-8B-heretic-int4-cw-ov
                              ↓ symlink
               ~/NoLlama/model  →  NPU inference :11435
```

After deploy, enable LLM polish:

```bash
export HCC_LLM_ENABLED=1
export HCC_LLM_URL=http://127.0.0.1:11435
python3 scripts/run_daily.py --force
```

### Synthetic data + LoRA

On the rented GPU with Ollama running a large model:

```bash
# Generate 2000 synthetic property email replies
hcc gpu-day generate gpu-day-kit/exports/synthetic_batch.jsonl \
  --url http://127.0.0.1:11434 --model qwen3:30b

# Optional: polish all 218 outreach drafts
hcc gpu-day generate gpu-day-kit/exports/outreach_batch.jsonl \
  --url http://127.0.0.1:11434 --model qwen3:8b

# Convert to training JSONL
hcc gpu-day merge gpu-day-kit/exports/synthetic_batch_generated.jsonl \
  --include-outreach gpu-day-kit/exports/outreach_batch_generated.jsonl
```

Train with LLaMA-Factory / Axolotl using `lora/housing_case_manager.yaml` and `exports/housing_case_manager_train.jsonl`.

## File layout

```
gpu-day-kit/
  config.env.example    # paths and endpoints
  run.sh                # master runner
  exports/              # generated bundles and batches
  prompts/              # benchmark + synthetic templates
  schemas/              # JSON schemas for parser agent
  scripts/              # Python + shell pipeline
  lora/                 # fine-tune config
```

## Other GPU day ideas (if time remains)

- Run embeddings over 218 property descriptions for semantic search
- Benchmark Qwen3-30B on hard briefing tasks (set `HCC_GPU_LLM_MODEL`)
- Generate call scripts for properties with phone-only contacts
- Export LoRA-merged weights back through OpenVINO for NPU deploy