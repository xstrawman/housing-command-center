#!/usr/bin/env bash
# Export Heretic weights to OpenVINO INT4 (matches NoLlama Qwen3-8B-int4-cw-ov layout)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$KIT/config.env" ]]; then
  # shellcheck source=/dev/null
  source "$KIT/config.env"
fi

SOURCE="${OV_SOURCE:-${HERETIC_OUTPUT:-$HOME/models/Qwen3-8B-heretic}}"
OUTPUT="${OV_OUTPUT:-$HOME/models/Qwen3-8B-heretic-int4-cw-ov}"
FORMAT="${OV_WEIGHT_FORMAT:-int4}"
DATASET="${OV_DATASET:-c4}"

echo "═══ OpenVINO export ═══"
echo "  source: $SOURCE"
echo "  output: $OUTPUT"
echo "  format: $FORMAT (symmetric CW — matches existing NPU model)"
echo ""

if [[ ! -d "$SOURCE" ]]; then
  echo "Source model not found: $SOURCE" >&2
  echo "Run run_heretic.sh first, or set OV_SOURCE to HF weights." >&2
  exit 1
fi

# Prefer NoLlama venv (has optimum-intel + openvino toolchain)
if [[ -d "$HOME/NoLlama/venv/bin" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/NoLlama/venv/bin/activate"
elif [[ -d "$HOME/agentic-ai/venv/bin" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/agentic-ai/venv/bin/activate"
fi

if ! command -v optimum-cli &>/dev/null; then
  echo "Installing optimum[openvino]…"
  pip install -U "optimum[openvino]" openvino openvino-tokenizers nncf
fi

mkdir -p "$OUTPUT"

# INT4 symmetric — same recipe as OpenVINO/Qwen3-8B-int4-cw-ov README
optimum-cli export openvino \
  --model "$SOURCE" \
  --task text-generation-with-past \
  --weight-format "$FORMAT" \
  --sym \
  --ratio 1.0 \
  --dataset "$DATASET" \
  --trust-remote-code \
  "$OUTPUT"

echo ""
echo "Export complete: $OUTPUT"
echo "Verify files:"
ls -lh "$OUTPUT"/openvino_model.* 2>/dev/null || true
echo ""
echo "Next: gpu-day-kit/scripts/deploy_to_nollama.sh"