#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"

echo "╔══════════════════════════════════════════════════╗"
echo "║       Ethara AI × ARC  —  Web Runner            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Host:    $HOST                                  "
echo "║  Port:    $PORT                                  "
echo "║  Workers: $WORKERS                               "
echo "╚══════════════════════════════════════════════════╝"

exec gunicorn \
    --worker-class eventlet \
    --workers "$WORKERS" \
    --bind "${HOST}:${PORT}" \
    --timeout 120 \
    --keep-alive 65 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    web.server:app
