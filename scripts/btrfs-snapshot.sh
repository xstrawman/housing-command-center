#!/usr/bin/env bash
# Manual btrfs snapshots for CachyOS layout (@, @home on /dev/nvme0n1p2)
# Snapshots are read-only subvolumes at @snapshots/ on the btrfs root (subvolid=5).
set -euo pipefail

DEVICE="${BTRFS_DEVICE:-/dev/nvme0n1p2}"
STAMP="${1:-$(date +%Y%m%d-%H%M%S)}"
LABEL="${2:-manual}"
MNT="$(mktemp -d /tmp/btrfs-snap.XXXXXX)"
SNAP_DIR="@snapshots"

cleanup() {
  sudo umount "$MNT" 2>/dev/null || true
  rmdir "$MNT" 2>/dev/null || true
}
trap cleanup EXIT

if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
  echo "Root required. Run: sudo $0"
  exit 1
fi

run() {
  if [[ $EUID -eq 0 ]]; then "$@"; else sudo "$@"; fi
}

echo "═══ btrfs snapshot — $STAMP ($LABEL) ═══"
echo "Device: $DEVICE"

run mount -o subvolid=5,subvol=/ "$DEVICE" "$MNT"
run mkdir -p "$MNT/$SNAP_DIR"

snapshot_one() {
  local src="$1" tag="$2"
  local dest="$MNT/$SNAP_DIR/${tag}-${LABEL}-${STAMP}"
  if [[ ! -d "$MNT/$src" ]]; then
    echo "Skip $src (not found)" >&2
    return 0
  fi
  echo "Snapshot: $src → @snapshots/${tag}-${LABEL}-${STAMP}"
  run btrfs subvolume snapshot -r "$MNT/$src" "$dest"
}

snapshot_one "@" "root"
snapshot_one "@home" "home"

echo ""
echo "Snapshots on $DEVICE:"
run btrfs subvolume list "$MNT/$SNAP_DIR" | tail -10
echo ""
echo "Done. Restore example:"
echo "  sudo mount -o subvolid=5,subvol=/ $DEVICE /mnt"
echo "  sudo btrfs subvolume snapshot /mnt/@snapshots/root-${LABEL}-${STAMP} /mnt/@-restored"