#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$project_root"

require_compose
ensure_local_env

info "Validating Docker Compose configuration..."
"${COMPOSE[@]}" config --quiet

cat <<'EOF'

Local prerequisites are ready.

Next:
  ./dev.sh up                 Start the stack and seed an empty database
  ./dev.sh logs               Follow all logs
  ./dev.sh logs fusion-service
  ./dev.sh smoke              Run end-to-end smoke checks

Optional Linux webcam:
  HAR_WEBCAM=true ./dev.sh up
EOF
