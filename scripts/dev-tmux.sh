#!/usr/bin/env bash
#
# Spin up the full local dev stack for the-saas-template in a tmux session.
#
# Usage:
#   ./scripts/dev-tmux.sh                 # no ngrok pane
#   ./scripts/dev-tmux.sh --ngrok <URL>   # adds an ngrok pane bound to backend (:8000)
#
# Layout (one session, two windows):
#   window "app":
#     TL  supabase start            (gates the rest via tmux wait-for)
#     TR  backend  : make dev       (port 8000)
#     BL  frontend : pnpm i && pnpm run dev (port 5173)
#     BR  free shell at repo root
#         (optional split: ngrok http --url=<URL> 8000)
#   window "engine":
#     L   engine   : make dev-gateway (port 8001)
#     R   engine   : make dev-worker

set -euo pipefail

SESSION="sst"
NGROK_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ngrok)
      [[ $# -lt 2 ]] && { echo "--ngrok requires a URL argument" >&2; exit 1; }
      NGROK_URL="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,15p' "$0"; exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2; exit 1
      ;;
  esac
done

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

command -v tmux >/dev/null || { echo "tmux is not installed" >&2; exit 1; }

# Ensure Docker is running (Supabase needs it). Mirrors the dpd helper in ~/.zshrc.
ensure_docker() {
  command -v docker >/dev/null 2>&1 || { echo "docker CLI not found on PATH." >&2; return 1; }
  if docker info >/dev/null 2>&1; then return 0; fi

  echo "Starting Docker Desktop..."
  if [[ "$(uname)" == "Darwin" ]]; then
    open -g -a Docker
  else
    echo "Docker is not running; please start it manually." >&2
    return 1
  fi

  local timeout=120 start_ts
  start_ts=$(date +%s)
  echo -n "Waiting for Docker to be ready"
  while ! docker info >/dev/null 2>&1; do
    if (( $(date +%s) - start_ts >= timeout )); then
      echo; echo "Docker did not become ready within ${timeout}s." >&2; return 1
    fi
    echo -n "."; sleep 2
  done
  echo " ready."
}

ensure_docker || exit 1

tmux kill-session -t "$SESSION" 2>/dev/null || true

# ---- window 1: app -----------------------------------------------------------
tmux new-session -d -s "$SESSION" -n app
TL=$(tmux display-message -p -t "$SESSION:app.0" "#{pane_id}")
TR=$(tmux split-window -h -t "$TL" -P -F "#{pane_id}")
BL=$(tmux split-window -v -t "$TL" -P -F "#{pane_id}")
BR=$(tmux split-window -v -t "$TR" -P -F "#{pane_id}")

# DB-ready gate (same pattern as lucent_template_layout.sh)
DB_SIGNAL="sst_db_ready"
tmux set-environment -g SST_DB_STATUS "" 2>/dev/null || true

# TL: start Supabase, then signal the gate when port 54321 is reachable
tmux send-keys -t "$TL" "cd \"$PROJECT_DIR/backend\" && supabase start & sleep 1; timeout=300; start_ts=\$(date +%s); ready=false; while true; do if command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 54321 2>/dev/null; then ready=true; break; fi; if curl -s http://127.0.0.1:54321 >/dev/null 2>&1; then ready=true; break; fi; if (( \$(date +%s) - start_ts >= timeout )); then break; fi; sleep 2; done; if [ \"\$ready\" = true ]; then tmux set-environment -g SST_DB_STATUS ok; else tmux set-environment -g SST_DB_STATUS fail; echo \"Timed out waiting for Supabase (300s)\"; fi; tmux wait-for -S \"$DB_SIGNAL\"" Enter

# Helper: wait on the DB signal then run a command (avoid zsh reserved 'status')
wait_then() {
  local pane="$1" dir="$2" cmd="$3" label="$4"
  tmux send-keys -t "$pane" "cd \"$dir\" && tmux wait-for \"$DB_SIGNAL\"; db_status=\$(tmux show-environment -g SST_DB_STATUS 2>/dev/null | sed -E 's/^SST_DB_STATUS=//'); if [ \"\$db_status\" = ok ]; then $cmd; else echo \"Not starting $label (db=\$db_status)\"; fi" Enter
}

wait_then "$TR" "$PROJECT_DIR/backend"  "make dev"            "backend"
wait_then "$BL" "$PROJECT_DIR/frontend" "pnpm i && pnpm run dev" "frontend"

# BR: free shell, plus optional ngrok split
tmux send-keys -t "$BR" "cd \"$PROJECT_DIR\"" Enter
if [[ -n "$NGROK_URL" ]]; then
  NG=$(tmux split-window -h -t "$BR" -P -F "#{pane_id}")
  tmux send-keys -t "$NG" "cd \"$PROJECT_DIR\" && ngrok http --url=$NGROK_URL 8000" Enter
fi

# ---- window 2: engine --------------------------------------------------------
tmux new-window -t "$SESSION:" -n engine
EL=$(tmux display-message -p -t "$SESSION:engine.0" "#{pane_id}")
ER=$(tmux split-window -h -t "$EL" -P -F "#{pane_id}")

wait_then "$EL" "$PROJECT_DIR/engine" "make dev-gateway" "engine gateway"
wait_then "$ER" "$PROJECT_DIR/engine" "make dev-worker"  "engine worker"

# Focus the supabase pane and attach
tmux select-window -t "$SESSION:app"
tmux select-pane -t "$TL"
tmux attach -t "$SESSION"
