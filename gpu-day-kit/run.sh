#!/usr/bin/env bash
# GPU day kit — master entry point
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$KIT/scripts"

if [[ -f "$KIT/config.env" ]]; then
  # shellcheck source=/dev/null
  source "$KIT/config.env"
fi

cmd="${1:-help}"
shift || true

case "$cmd" in
  export)
    exec python3 "$SCRIPTS/export_bundle.py" "$@"
    ;;
  prefill-outreach)
    exec python3 "$SCRIPTS/prefill_outreach.py" "$@"
    ;;
  prefill-synthetic)
    exec python3 "$SCRIPTS/prefill_synthetic.py" "$@"
    ;;
  benchmark)
    exec python3 "$SCRIPTS/benchmark.py" "$@"
    ;;
  generate)
    exec python3 "$SCRIPTS/batch_generate.py" "$@"
    ;;
  merge)
    exec python3 "$SCRIPTS/merge_synthetic.py" "$@"
    ;;
  heretic)
    exec bash "$SCRIPTS/run_heretic.sh" "$@"
    ;;
  openvino)
    exec bash "$SCRIPTS/export_openvino.sh" "$@"
    ;;
  deploy)
    exec bash "$SCRIPTS/deploy_to_nollama.sh" "$@"
    ;;
  prep)
    echo "═══ GPU day prep (no GPU needed) ═══"
    python3 "$SCRIPTS/export_bundle.py"
    python3 "$SCRIPTS/prefill_outreach.py" --mode all
    python3 "$SCRIPTS/prefill_synthetic.py" --count "${SYNTH_EMAIL_REPLIES:-2000}"
    echo ""
    echo "Ready. On GPU rental day:"
    echo "  gpu-day-kit/run.sh heretic"
    echo "  gpu-day-kit/run.sh openvino"
    echo "  gpu-day-kit/run.sh deploy"
    echo "  gpu-day-kit/run.sh benchmark --compare"
    echo "  gpu-day-kit/run.sh generate exports/synthetic_batch.jsonl --url \$HCC_GPU_LLM_URL"
    echo "  gpu-day-kit/run.sh merge exports/synthetic_batch_generated.jsonl"
    ;;
  help|*)
    cat <<EOF
Housing Command Center — GPU Day Kit

  ./run.sh prep              Export data + prefill batches (run now)
  ./run.sh export            Export DB bundle
  ./run.sh prefill-outreach  Build outreach JSONL for 218 properties
  ./run.sh prefill-synthetic Build 2000 synthetic email-reply prompts
  ./run.sh benchmark         Run agent prompt benchmarks
  ./run.sh generate FILE     Batch-generate with GPU Ollama
  ./run.sh merge FILE        Convert outputs → LoRA training JSONL

  ./run.sh heretic           Step 1: Heretic abliteration (GPU)
  ./run.sh openvino          Step 2: Export OpenVINO INT4
  ./run.sh deploy            Step 3: Deploy to NoLlama NPU

Config: copy config.env.example → config.env
From PC: hcc gpu-day [command]
EOF
    ;;
esac