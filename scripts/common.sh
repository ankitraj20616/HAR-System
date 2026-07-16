#!/usr/bin/env bash

# Shared shell helpers for repository-local developer commands.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' was not found."
}

compose_command() {
  COMPOSE=(docker compose)
  if [[ "${HAR_WEBCAM:-false}" == "true" ]]; then
    COMPOSE+=(-f docker-compose.yml -f docker-compose.webcam.yml)
  fi
}

require_compose() {
  require_command docker
  docker compose version >/dev/null 2>&1 || die \
    "Docker Compose v2 is required (the 'docker compose' command)."
  docker info >/dev/null 2>&1 || die \
    "Docker is not reachable. Start Docker Engine/Desktop and retry."
  compose_command
}

ensure_local_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    info "Created .env from .env.example (safe local defaults)."
  fi
  mkdir -p data/models
}

require_auth_env() {
  [[ -f .env ]] || die "Run './dev.sh setup', then configure auth in .env."
  if grep --quiet '^JWT_SECRET=replace-with-at-least-32-random-characters$' .env \
    || grep --quiet '^AUTH_TICKET_SECRET=replace-with-at-least-32-random-characters$' .env; then
    die "Configure JWT_SECRET and AUTH_TICKET_SECRET in .env. Use: openssl rand -hex 32"
  fi
}

service_exists() {
  local wanted="$1"
  "${COMPOSE[@]}" config --services | grep --fixed-strings --line-regexp --quiet "$wanted"
}
