#!/usr/bin/env bash
# Interactive demo UI on http://localhost:8000: the real agent (real model calls) on a fresh in-memory store.
# Needs Docker and ANTHROPIC_API_KEY in .env. Ctrl-C to stop.
set -euo pipefail
cd "$(dirname "$0")"

docker compose build -q api
( until curl -sf localhost:8000/customers >/dev/null; do sleep 1; done
  echo "Demo running on http://localhost:8000"; open http://localhost:8000 2>/dev/null || true ) &
# Bound to localhost only: the demo server has no customer auth.
exec docker compose run --rm -p 127.0.0.1:8000:8000 -v "$PWD/demo:/app/demo:ro" api \
  uvicorn demo.server:api --host 0.0.0.0 --port 8000
