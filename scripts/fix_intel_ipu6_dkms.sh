#!/usr/bin/env bash

set -euo pipefail

LOG_PATH="/var/lib/dkms/ipu6-drivers/0~git202406240945.aecec2aa-0ubuntu2~24.04.3/build/make.log"
CRASH_REPORT="/var/crash/intel-ipu6-dkms.0.crash"

show_usage() {
  cat <<'EOF'
Usage: fix_intel_ipu6_dkms.sh [--purge]

Actions:
  1. Remove the stale IPU6 crash report so DKMS can write a new one.
  2. Display the tail of the DKMS build log for quick inspection.
  3. Re-run dpkg configuration to finish the interrupted apt transaction.
  4. Optionally purge intel-ipu6-dkms (when --purge is provided).
EOF
}

maybe_show_usage() {
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    show_usage
    exit 0
  fi
}

maybe_purge=false
if [[ $# -gt 0 ]]; then
  maybe_show_usage "$1"
fi

if [[ "${1:-}" == "--purge" ]]; then
  maybe_purge=true
elif [[ $# -gt 0 ]]; then
  echo "Unknown argument: $1" >&2
  show_usage >&2
  exit 1
fi

echo "[1/4] Removing stale crash report at ${CRASH_REPORT} (if it exists)..."
if sudo test -f "$CRASH_REPORT"; then
  sudo rm -f "$CRASH_REPORT"
  echo "Removed ${CRASH_REPORT}."
else
  echo "Crash report not found; nothing to remove."
fi

echo "[2/4] Showing the last 40 lines of the DKMS build log (${LOG_PATH})..."
if sudo test -f "$LOG_PATH"; then
  sudo tail -n 40 "$LOG_PATH"
else
  echo "Log file not found. The intel-ipu6-dkms package may already be removed."
fi

echo "[3/4] Reconfiguring pending packages (this may re-run DKMS build)..."
sudo dpkg --configure -a

if $maybe_purge; then
  echo "[4/4] Purging intel-ipu6-dkms as requested..."
  sudo apt remove --purge -y intel-ipu6-dkms
else
  echo "[4/4] Skipping package removal. Re-run with --purge to remove intel-ipu6-dkms."
fi

echo "Done."
