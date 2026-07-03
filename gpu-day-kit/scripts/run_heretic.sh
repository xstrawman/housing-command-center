#!/usr/bin/env bash
# Abliterate Qwen3-8B with Heretic (GPU rental step 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$KIT/config.env" ]]; then
  # shellcheck source=/dev/null
  source "$KIT/config.env"
fi

MODEL="${HERETIC_MODEL:-Qwen/Qwen3-8B}"
OUTPUT="${HERETIC_OUTPUT:-$HOME/models/Qwen3-8B-heretic}"
QUANT="${HERETIC_QUANTIZATION:-}"

echo "═══ Heretic abliteration ═══"
echo "  model:  $MODEL"
echo "  output: $OUTPUT"
echo ""

if ! command -v heretic &>/dev/null; then
  echo "Installing heretic-llm…"
  pip install -U heretic-llm
fi

mkdir -p "$(dirname "$OUTPUT")"

ARGS=(--model "$MODEL" --output-dir "$OUTPUT")
if [[ -n "$QUANT" ]]; then
  ARGS+=(--quantization "$QUANT")
fi

echo "Running: heretic ${ARGS[*]}"
heretic "${ARGS[@]}"

echo ""
echo "Done. Weights at: $OUTPUT"
echo "Next: gpu-day-kit/scripts/export_openvino.sh"