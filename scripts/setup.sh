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

Required before starting:
  Edit .env with your Supabase URL, publishable key, and a random 32+ character
  AUTH_TICKET_SECRET. Follow core_docs/milestones/milestone-6-auth-rbac/SUPABASE_SETUP.md.

Next:
  ./dev.sh up                 Start the stack and seed an empty database
  ./dev.sh logs               Follow all logs
  ./dev.sh logs fusion-service
  ./dev.sh smoke              Run end-to-end smoke checks

Optional Linux webcam:
  HAR_WEBCAM=true ./dev.sh up
EOF
