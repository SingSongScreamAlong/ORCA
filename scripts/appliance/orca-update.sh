#!/usr/bin/env bash
# ORCA appliance update — pull released source from GitHub and rebuild in place.
#
# The sealed-appliance deploy step. The VM only ever pulls *released source* from
# origin (reached out through the VPN) and rebuilds from it; nothing is hand-edited
# on the appliance, so its running state is always reproducible from a single git
# commit. For a tool that handles case evidence, that reproducibility is the point —
# "what was tested" and "what runs" are guaranteed identical, and the box stays
# auditable and clean.
#
# What it does (idempotent):
#   1. git fetch + reset --hard origin/<branch>   → byte-identical to the pushed commit
#   2. backend  — venv + pip install (+ alembic upgrade head only when on Postgres)
#   3. frontend — npm ci + next build (production build)
#   4. restart the orca-backend / orca-frontend services (systemd --user)
#
# Usage:
#   ~/orca-update.sh                     # track the configured branch (default: main)
#   ORCA_BRANCH=release ~/orca-update.sh # track a different branch
#   ORCA_HOME=/path/to/ORCA ~/orca-update.sh   # point at a specific checkout
#
# Exit non-zero on any failure so a bad pull/build never leaves a half-updated box.
set -euo pipefail

BRANCH="${ORCA_BRANCH:-main}"

# --- locate the checkout (auto-detect, like the appliance owner expects) --------
_detect_checkout() {
  local here candidates d
  here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
  candidates=(
    "${ORCA_HOME:-}"
    "$here/../.."                      # running from inside the repo's scripts/appliance
    "/home/orca/ORCA"
    "$HOME/ORCA"
    "/opt/ORCA"
  )
  for d in "${candidates[@]}"; do
    [ -n "$d" ] || continue
    if [ -d "$d/.git" ] && [ -f "$d/backend/pyproject.toml" ]; then
      readlink -f "$d"
      return 0
    fi
  done
  return 1
}

REPO="$(_detect_checkout)" || {
  echo "ERROR: ORCA checkout not found. Set ORCA_HOME=/path/to/ORCA and retry." >&2
  exit 1
}

# --- run as the checkout's owner (so a root-triggered run doesn't poison perms) --
OWNER="$(stat -c '%U' "$REPO")"
if [ "$(id -un)" != "$OWNER" ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -u "$OWNER" ORCA_BRANCH="$BRANCH" ORCA_HOME="$REPO" "$(readlink -f "$0")" "$@"
  fi
  echo "ERROR: must run as '$OWNER' (the checkout owner); sudo unavailable." >&2
  exit 1
fi

echo "==> ORCA appliance update — $REPO @ origin/$BRANCH (as $OWNER)"
cd "$REPO"

# --- 1. pull released source; discard any local drift ---------------------------
git fetch --prune origin
git reset --hard "origin/$BRANCH"
git -c log.showsignature=false log -1 --format='    now at %h  %s'

# --- 2. backend: venv + dependencies (+ migrations only on Postgres) ------------
echo "==> backend: venv + dependencies"
cd "$REPO/backend"
[ -d .venv ] || python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e .
if [ "${ORCA_STORAGE_BACKEND:-memory}" = "postgres" ]; then
  echo "    storage=postgres → alembic upgrade head"
  alembic upgrade head
fi
deactivate

# --- 3. frontend: clean install + production build ------------------------------
echo "==> frontend: install + production build"
cd "$REPO/frontend"
if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build

# --- 4. restart the appliance services (best-effort) ----------------------------
if command -v systemctl >/dev/null 2>&1 && systemctl --user list-unit-files 2>/dev/null | grep -q '^orca-'; then
  echo "==> restarting services"
  systemctl --user restart orca-backend.service orca-frontend.service
  systemctl --user --no-pager --lines=0 status orca-backend.service orca-frontend.service || true
else
  echo "==> services not installed under systemd --user yet"
  echo "    see scripts/appliance/README.md to install orca-backend / orca-frontend"
fi

echo "==> ORCA is up to date and rebuilt (origin/$BRANCH)."
