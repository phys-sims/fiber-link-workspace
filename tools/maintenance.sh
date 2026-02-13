#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPS_DIR="$ROOT/deps"

usage() {
  cat <<'EOF'
Usage: tools/maintenance.sh [--full] [--status-only]

Defaults to a safe update that preserves local branches and dirty repos.

Options:
  --full         Run a clean, deterministic refresh (resets/cleans repos).
  --status-only  Skip bootstrap; only print repo status summary.
  -h, --help     Show this help message.
EOF
}

FULL_REFRESH=0
STATUS_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --full)
      FULL_REFRESH=1
      ;;
    --status-only)
      STATUS_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$STATUS_ONLY" -eq 0 ]]; then
  if [[ "$FULL_REFRESH" -eq 1 ]]; then
    echo "==> Running bootstrap (full refresh)"
    python "$ROOT/tools/bootstrap.py"
  else
    echo "==> Running bootstrap (preserve local work)"
    BOOTSTRAP_PRESERVE_LOCAL=1 python "$ROOT/tools/bootstrap.py"
  fi
fi

echo "==> Repo status summary"
if [[ ! -d "$DEPS_DIR" ]]; then
  echo "deps/ not found; run tools/bootstrap.py first." >&2
  exit 1
fi

for repo in "$DEPS_DIR"/*; do
  if [[ -d "$repo/.git" ]]; then
    echo "-- $(basename "$repo")"
    git -C "$repo" status -sb
  fi
done
