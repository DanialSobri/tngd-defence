#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${SCRIPT_DIR}"
SESSION_NAME="${1:-tngd-backend}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"

if ! command -v screen >/dev/null 2>&1; then
  echo "screen is not installed. Install it first (e.g. sudo apt-get install -y screen)."
  exit 1
fi

if ! command -v python3.10 >/dev/null 2>&1; then
  echo "python3.10 not found. Install Python 3.10 before deploying."
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3.10 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
pip install -r "${APP_DIR}/requirements.txt"

if screen -list | rg -q "[[:space:]]${SESSION_NAME}[[:space:]]"; then
  echo "Stopping existing screen session: ${SESSION_NAME}"
  screen -S "${SESSION_NAME}" -X quit
fi

CMD="cd \"${APP_DIR}\" && source \"${VENV_DIR}/bin/activate\" && uvicorn main:app --host ${HOST} --port ${PORT}"
screen -dmS "${SESSION_NAME}" bash -lc "${CMD}"

echo "Backend deployed in screen session: ${SESSION_NAME}"
echo "Attach: screen -r ${SESSION_NAME}"
echo "List sessions: screen -ls"
