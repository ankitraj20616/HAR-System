#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/common.sh"
cd "$project_root"

usage() {
  cat <<'EOF'
HAR local stack helper

Usage:
  ./dev.sh setup                 Check prerequisites and create .env
  ./dev.sh up                    Build/start stack; seed DB only when empty
  ./dev.sh down                  Stop stack; preserve database volumes
  ./dev.sh logs [service]        Follow all logs or one service
  ./dev.sh status                Show container and endpoint status
  ./dev.sh restart [service]     Restart the stack or one service
  ./dev.sh seed                  Replace DB content with prototype data
  ./dev.sh smoke                 Run the end-to-end smoke test
  ./dev.sh config                Render and validate Compose configuration
  ./dev.sh help                  Show this help

Examples:
  ./dev.sh up
  ./dev.sh logs fusion-service
  HAR_WEBCAM=true ./dev.sh up
EOF
}

action="${1:-help}"
shift || true

case "$action" in
  setup)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh setup"
    exec ./scripts/setup.sh
    ;;
  up)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh up"
    require_compose
    ensure_local_env
    info "Starting PostgreSQL and MQTT prerequisites..."
    "${COMPOSE[@]}" config --quiet
    "${COMPOSE[@]}" up --detach --wait \
      --wait-timeout "${DEV_WAIT_TIMEOUT_SECONDS:-240}" postgres mosquitto
    ./scripts/seed.sh --if-empty
    info "Building and starting HAR application services..."
    "${COMPOSE[@]}" up --detach --build --wait \
      --wait-timeout "${DEV_WAIT_TIMEOUT_SECONDS:-240}" --remove-orphans
    cat <<'EOF'

HAR prototype is ready:
  Dashboard:    http://localhost:5173
  Fusion API:  http://localhost:8001/docs
  Feedback API:http://localhost:8002/docs

Use './dev.sh logs' to follow logs and './dev.sh down' to stop.
EOF
    ;;
  down)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh down"
    require_compose
    info "Stopping the HAR stack (saved data is preserved)..."
    "${COMPOSE[@]}" down --remove-orphans
    ;;
  logs)
    [[ $# -le 1 ]] || die "Usage: ./dev.sh logs [service]"
    require_compose
    if [[ $# -eq 1 ]]; then
      service="${1//_/-}"
      service_exists "$service" || die \
        "Unknown service '$1'. Available: $("${COMPOSE[@]}" config --services | tr '\n' ' ')"
      exec "${COMPOSE[@]}" logs --follow --tail "${LOG_TAIL:-200}" "$service"
    fi
    exec "${COMPOSE[@]}" logs --follow --tail "${LOG_TAIL:-200}"
    ;;
  status|ps)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh status"
    require_compose
    require_command curl
    "${COMPOSE[@]}" ps
    echo
    for endpoint in \
      http://localhost:8001/health \
      http://localhost:8002/health \
      http://localhost:8003/health \
      http://localhost:8004/health \
      http://localhost:5173/health; do
      if curl --fail --silent --max-time 2 "$endpoint" >/dev/null 2>&1; then
        echo "OK    $endpoint"
      else
        echo "DOWN  $endpoint"
      fi
    done
    ;;
  restart)
    [[ $# -le 1 ]] || die "Usage: ./dev.sh restart [service]"
    require_compose
    if [[ $# -eq 1 ]]; then
      service="${1//_/-}"
      service_exists "$service" || die "Unknown service '$1'."
      "${COMPOSE[@]}" restart "$service"
    else
      "${COMPOSE[@]}" restart
    fi
    ;;
  seed)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh seed"
    exec ./scripts/seed.sh
    ;;
  smoke)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh smoke"
    exec ./scripts/smoke.sh
    ;;
  config)
    [[ $# -eq 0 ]] || die "Usage: ./dev.sh config"
    require_compose
    "${COMPOSE[@]}" config
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    die "Unknown command '$action'."
    ;;
esac
