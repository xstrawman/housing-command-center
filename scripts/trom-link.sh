#!/usr/bin/env bash
# Link Housing Command Center to Trom Files (Nextcloud at files.trom.tf)
set -euo pipefail

CREDS="${HCC_TROM_ENV:-$HOME/.config/hcc/trom.env}"
RCLONE="${RCLONE_BIN:-$HOME/.local/bin/rclone}"
REMOTE="${TROM_RCLONE_REMOTE:-trom}"

if [[ ! -f "$CREDS" ]]; then
  echo "Missing credentials: $CREDS" >&2
  echo "Copy scripts/trom.env.example to ~/.config/hcc/trom.env and edit." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$CREDS"
chmod 600 "$CREDS" 2>/dev/null || true

if [[ ! -x "$RCLONE" ]]; then
  echo "rclone not found at $RCLONE" >&2
  echo "Install: unzip rclone to ~/.local/bin/rclone" >&2
  exit 1
fi

cmd="${1:-status}"
shift || true

configure_remote() {
  "$RCLONE" config delete "$REMOTE" 2>/dev/null || true
  "$RCLONE" config create "$REMOTE" webdav \
    url "$TROM_WEBDAV" \
    vendor nextcloud \
    user "$TROM_USER" \
    pass "$TROM_PASS"
  echo "Configured rclone remote: $REMOTE"
}

case "$cmd" in
  configure|link)
    configure_remote
    ;;
  test|status)
    if ! "$RCLONE" listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
      echo "No rclone remote '$REMOTE' — running configure…"
      configure_remote
    fi
    echo "Testing Trom connection…"
    if "$RCLONE" lsd "${REMOTE}:" "$@"; then
      echo "OK — Trom account linked."
    else
      echo "" >&2
      echo "Authentication failed." >&2
      echo "1. Log in at https://files.trom.tf in your browser (verify username/password)." >&2
      echo "2. If needed, register at https://files.trom.tf/apps/registration/" >&2
      echo "3. Create an App Password: Settings → Security → Create new app password" >&2
      echo "4. Put that app password in $CREDS as TROM_PASS" >&2
      echo "5. Run: hcc trom link" >&2
      exit 1
    fi
    ;;
  ls|list)
    "$RCLONE" ls "${REMOTE}:${1:-}" "${@:2}"
    ;;
  sync)
    # Sync HCC exports + docs to Trom
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    DEST="${1:-HousingCommandCenter}"
    echo "Syncing to ${REMOTE}:${DEST}/"
    "$RCLONE" sync "$ROOT/gpu-day-kit/exports" "${REMOTE}:${DEST}/gpu-exports" --progress
    "$RCLONE" copy "$ROOT/docs" "${REMOTE}:${DEST}/docs" --progress
    "$RCLONE" copy "$ROOT/dist" "${REMOTE}:${DEST}/dist" --progress 2>/dev/null || true
    echo "Done."
    ;;
  mount)
    MNT="${1:-$HOME/TromFiles}"
    mkdir -p "$MNT"
    echo "Mounting ${REMOTE}: at $MNT (Ctrl+C to unmount)"
    "$RCLONE" mount "${REMOTE}:" "$MNT" --vfs-cache-mode writes
    ;;
  *)
    cat <<EOF
Trom Files (files.trom.tf) — Nextcloud link

  hcc trom link       Configure + test connection
  hcc trom status     Test connection
  hcc trom ls [path]  List remote files
  hcc trom sync       Upload HCC exports/docs to Trom
  hcc trom mount      Mount remote at ~/TromFiles

Credentials: ~/.config/hcc/trom.env
EOF
    ;;
esac