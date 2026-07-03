#!/usr/bin/env bash
# Deploy OpenVINO model to NoLlama and restart service
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$KIT/config.env" ]]; then
  # shellcheck source=/dev/null
  source "$KIT/config.env"
fi

OV_MODEL="${OV_OUTPUT:-$HOME/models/Qwen3-8B-heretic-int4-cw-ov}"
NOLLAMA_ROOT="${NOLLAMA_ROOT:-$HOME/NoLlama}"
LINK="${NOLLAMA_MODEL_LINK:-$NOLLAMA_ROOT/model}"
PORT="${NOLLAMA_PORT:-11435}"

echo "═══ Deploy to NoLlama ═══"
echo "  model: $OV_MODEL"
echo "  link:  $LINK"
echo ""

if [[ ! -f "$OV_MODEL/openvino_model.xml" ]]; then
  echo "OpenVINO model not found at $OV_MODEL" >&2
  exit 1
fi

# Backup current model
if [[ -L "$LINK" || -d "$LINK" ]]; then
  backup="$NOLLAMA_ROOT/model.backup.$(date +%Y%m%d%H%M%S)"
  echo "Backing up current model → $backup"
  mv "$LINK" "$backup"
fi

ln -sfn "$OV_MODEL" "$LINK"
echo "Linked $LINK → $OV_MODEL"

# Restart NoLlama if running
if pgrep -f "nollama.py.*$PORT" &>/dev/null; then
  echo "Restarting NoLlama on port $PORT…"
  pkill -f "nollama.py.*--ollama-port $PORT" || true
  sleep 2
fi

if [[ -x "$NOLLAMA_ROOT/start.sh" ]]; then
  cd "$NOLLAMA_ROOT"
  nohup ./start.sh > /tmp/nollama.log 2>&1 &
  sleep 3
fi

echo ""
echo "Smoke test:"
curl -sf "http://127.0.0.1:${PORT}/api/tags" | head -c 200 || echo "(NoLlama starting — wait a few seconds)"
echo ""
echo "Enable LLM polish in agents:"
echo "  export HCC_LLM_ENABLED=1"
echo "  export HCC_LLM_URL=http://127.0.0.1:${PORT}"
echo "  export HCC_LLM_MODEL=Qwen3-8B-int4-cw"
echo "  python3 scripts/run_daily.py --force"