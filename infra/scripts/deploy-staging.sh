#!/bin/bash
set -euo pipefail

# Brand Brain - Staging Deploy Script
# Usage: ./deploy-staging.sh [up|down|seed|logs]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../docker"
COMPOSE_FILE="$COMPOSE_DIR/compose.staging.yml"
ENV_FILE="$COMPOSE_DIR/.env.staging"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found."
  echo "Copy .env.staging.example to .env.staging and fill in the values."
  exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

cmd=${1:-up}

case "$cmd" in
  up)
    echo "Starting Brand Brain staging..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
    echo ""
    echo "Waiting for services to be ready..."
    sleep 5
    echo "Running migrations..."
    docker exec bb_api alembic upgrade head 2>/dev/null || echo "Alembic not available, skipping migrations"
    echo ""
    echo "Brand Brain staging is running at ${PUBLIC_URL:-http://localhost}"
    ;;
  down)
    echo "Stopping Brand Brain staging..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    ;;
  seed)
    echo "Seeding staging database..."
    docker exec bb_api python -m app.scripts.seed
    echo "Seed complete."
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f ${2:-}
    ;;
  *)
    echo "Usage: $0 [up|down|seed|logs]"
    exit 1
    ;;
esac
