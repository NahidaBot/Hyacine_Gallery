#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=${APP_DIR:-/opt/hyacine-gallery}
ENV_DIR=${ENV_DIR:-/etc/hyacine-gallery}
ENV_FILE=${ENV_FILE:-$ENV_DIR/hyacine-gallery.env}
DATA_DIR=${DATA_DIR:-/var/lib/hyacine-gallery}
SERVICE_USER=${SERVICE_USER:-hyacine-gallery}
SERVICE_GROUP=${SERVICE_GROUP:-hyacine-gallery}
SOURCE_DIR=${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
ORIGINAL_ARGS=("$@")

DO_SYNC=1
DO_DEPS=1
DO_BUILD=1
DO_MIGRATE=1
DO_SERVICES=1
DO_START=1
ENABLE_BOT=1
DRY_RUN=0

usage() {
  cat <<EOF
Install Hyacine Gallery as native systemd services.

Usage:
  sudo deploy/install-systemd.sh [options]

Options:
  --app-dir PATH        Application directory (default: $APP_DIR)
  --env-file PATH       Shared env file (default: $ENV_FILE)
  --data-dir PATH       Data directory (default: $DATA_DIR)
  --user NAME           Service user/group (default: $SERVICE_USER)
  --source-dir PATH     Source checkout to install from (default: $SOURCE_DIR)
  --no-sync             Do not sync source into APP_DIR
  --no-deps             Skip Python/Node dependency installation
  --no-build            Skip frontend build
  --no-migrate          Skip alembic upgrade
  --no-services         Skip installing systemd unit files
  --no-start            Install services but do not enable/start them
  --no-bot              Do not enable/start Telegram bot service
  --dry-run             Print planned actions without changing the system
  -h, --help            Show this help

Environment overrides:
  APP_DIR, ENV_FILE, DATA_DIR, SERVICE_USER, SERVICE_GROUP, SOURCE_DIR
EOF
}

log() {
  printf '\033[1;32m==>\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2
}

die() {
  printf '\033[1;31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      APP_DIR=$2
      shift 2
      ;;
    --env-file)
      ENV_FILE=$2
      ENV_DIR=$(dirname "$ENV_FILE")
      shift 2
      ;;
    --data-dir)
      DATA_DIR=$2
      shift 2
      ;;
    --user)
      SERVICE_USER=$2
      SERVICE_GROUP=$2
      shift 2
      ;;
    --source-dir)
      SOURCE_DIR=$2
      shift 2
      ;;
    --no-sync)
      DO_SYNC=0
      shift
      ;;
    --no-deps)
      DO_DEPS=0
      shift
      ;;
    --no-build)
      DO_BUILD=0
      shift
      ;;
    --no-migrate)
      DO_MIGRATE=0
      shift
      ;;
    --no-services)
      DO_SERVICES=0
      shift
      ;;
    --no-start)
      DO_START=0
      shift
      ;;
    --no-bot)
      ENABLE_BOT=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

if [[ ${EUID:-$(id -u)} -ne 0 && $DRY_RUN -eq 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "${ORIGINAL_ARGS[@]}"
  fi
  die "Run this script as root."
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    if [[ $DRY_RUN -eq 1 ]]; then
      warn "Missing command '$1'. Install will require it."
      return 0
    fi
    die "Missing command '$1'. Install it first."
  fi
}

run_cmd() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

run_as_service_user() {
  local command=$1
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run] run as %s: %s\n' "$SERVICE_USER" "$command"
    return 0
  fi
  if command -v runuser >/dev/null 2>&1; then
    runuser -u "$SERVICE_USER" -- bash -lc "$command"
  else
    su -s /bin/bash "$SERVICE_USER" -c "$command"
  fi
}

source_env_command() {
  local command=$1
  printf 'set -a; source %q; set +a; %s' "$ENV_FILE" "$command"
}

path_is_inside() {
  local child parent
  child=$(realpath -m "$1")
  parent=$(realpath -m "$2")
  [[ "$child" == "$parent" || "$child" == "$parent"/* ]]
}

env_needs_edit() {
  [[ -f "$ENV_FILE" ]] || return 0
  grep -Eq '^(DATABASE_URL=postgresql\+asyncpg://user:password@db\.example\.com|ADMIN_PANEL_SLUG=change-me|ADMIN_TOKEN=change-me|JWT_SECRET=change-me|TELEGRAM_BOT_USERNAME=your_bot_username)' "$ENV_FILE"
}

env_value() {
  local key=$1
  grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | sed -E "s/^['\"]|['\"]$//g" || true
}

log "Checking required commands"
require_command uv
require_command node
require_command systemctl
if [[ $DRY_RUN -eq 1 ]]; then
  warn "Dry run mode: no files, users, packages, migrations, or services will be changed."
fi

log "Creating service user and directories"
NOLOGIN_SHELL=/bin/false
for candidate in /usr/sbin/nologin /usr/bin/nologin /sbin/nologin; do
  if [[ -x "$candidate" ]]; then
    NOLOGIN_SHELL=$candidate
    break
  fi
done
if ! getent group "$SERVICE_GROUP" >/dev/null; then
  run_cmd groupadd --system "$SERVICE_GROUP"
else
  log "Group exists: $SERVICE_GROUP"
fi
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  run_cmd useradd --system --gid "$SERVICE_GROUP" --home "$APP_DIR" --shell "$NOLOGIN_SHELL" "$SERVICE_USER"
else
  log "User exists: $SERVICE_USER"
fi
run_cmd install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$APP_DIR"
run_cmd install -d -o root -g root "$ENV_DIR"
run_cmd install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$DATA_DIR/uploads"

if [[ $DO_SYNC -eq 1 ]]; then
  log "Syncing source from $SOURCE_DIR to $APP_DIR"
  if [[ ! -d "$SOURCE_DIR" ]]; then
    die "Source directory does not exist: $SOURCE_DIR"
  fi
  if [[ "$(realpath -m "$SOURCE_DIR")" != "$(realpath -m "$APP_DIR")" ]]; then
    if path_is_inside "$APP_DIR" "$SOURCE_DIR"; then
      die "APP_DIR must not be inside SOURCE_DIR when syncing."
    fi
    if command -v rsync >/dev/null 2>&1; then
      run_cmd rsync -a --delete \
        --exclude '.git/' \
        --exclude '.env' \
        --exclude '.env.*' \
        --exclude '**/.venv/' \
        --exclude '**/node_modules/' \
        --exclude '**/.next/' \
        --exclude '**/__pycache__/' \
        --exclude '**/.pytest_cache/' \
        --exclude '**/.mypy_cache/' \
        --exclude '**/.ruff_cache/' \
        --exclude 'backend/uploads/' \
        "$SOURCE_DIR/" "$APP_DIR/"
    else
      warn "rsync not found; using cp fallback without delete pruning."
      run_cmd cp -a "$SOURCE_DIR/." "$APP_DIR/"
    fi
  else
    log "Source and app directory are the same; skipping sync"
  fi
  run_cmd chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_DIR"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating $ENV_FILE from example"
  if [[ $DRY_RUN -eq 1 && ! -f "$APP_DIR/deploy/env/hyacine-gallery.env.example" ]]; then
    run_cmd install -m 0640 -o root -g "$SERVICE_GROUP" "$SOURCE_DIR/deploy/env/hyacine-gallery.env.example" "$ENV_FILE"
  else
    run_cmd install -m 0640 -o root -g "$SERVICE_GROUP" "$APP_DIR/deploy/env/hyacine-gallery.env.example" "$ENV_FILE"
  fi
else
  log "Keeping existing env file: $ENV_FILE"
fi

if [[ $DRY_RUN -eq 0 ]] && env_needs_edit; then
  cat <<EOF

Created or found env file with placeholder values:
  $ENV_FILE

Edit it before continuing, especially DATABASE_URL, ADMIN_PANEL_SLUG,
ADMIN_TOKEN, JWT_SECRET, BACKEND_URL, NEXT_PUBLIC_API_URL, and GALLERY_URL.

Then rerun:
  sudo $APP_DIR/deploy/install-systemd.sh --no-sync

EOF
  exit 2
fi

if [[ $DO_DEPS -eq 1 ]]; then
  log "Installing backend dependencies"
  run_as_service_user "cd '$APP_DIR/backend' && uv venv && uv pip install -e ."

  log "Installing Telegram bot dependencies"
  run_as_service_user "cd '$APP_DIR/bots/telegram' && uv venv && uv pip install -e ."

  log "Installing frontend dependencies"
  if command -v corepack >/dev/null 2>&1; then
    run_cmd corepack enable
  else
    warn "corepack not found; assuming pnpm is already available."
  fi
  require_command pnpm
  run_as_service_user "cd '$APP_DIR/frontend' && pnpm install --frozen-lockfile"
fi

if [[ $DO_BUILD -eq 1 ]]; then
  log "Building frontend"
  run_as_service_user "$(source_env_command "cd '$APP_DIR/frontend' && pnpm build")"
fi

if [[ $DO_MIGRATE -eq 1 ]]; then
  log "Running database migrations"
  run_as_service_user "$(source_env_command "cd '$APP_DIR/backend' && '$APP_DIR/backend/.venv/bin/alembic' upgrade head")"
fi

if [[ $DO_SERVICES -eq 1 ]]; then
  log "Installing systemd unit files"
  UNIT_SOURCE_DIR="$APP_DIR/deploy/systemd"
  if [[ $DRY_RUN -eq 1 && ! -d "$UNIT_SOURCE_DIR" ]]; then
    UNIT_SOURCE_DIR="$SOURCE_DIR/deploy/systemd"
  fi
  for unit in "$UNIT_SOURCE_DIR/"*.service; do
    unit_name=$(basename "$unit")
    if [[ $DRY_RUN -eq 1 ]]; then
      printf '[dry-run] render %s to /etc/systemd/system/%s\n' "$unit" "$unit_name"
    else
      sed \
        -e "s#/opt/hyacine-gallery#$APP_DIR#g" \
        -e "s#/etc/hyacine-gallery/hyacine-gallery.env#$ENV_FILE#g" \
        -e "s#^User=hyacine-gallery#User=$SERVICE_USER#" \
        -e "s#^Group=hyacine-gallery#Group=$SERVICE_GROUP#" \
        "$unit" >"/etc/systemd/system/$unit_name"
      chmod 0644 "/etc/systemd/system/$unit_name"
    fi
  done
  run_cmd systemctl daemon-reload
fi

if [[ $DO_START -eq 1 ]]; then
  log "Enabling and starting services"
  run_cmd systemctl enable --now hyacine-gallery-backend.service
  run_cmd systemctl enable --now hyacine-gallery-frontend.service
  if [[ $ENABLE_BOT -eq 1 ]]; then
    if [[ -n "$(env_value TELEGRAM_BOT_TOKEN)" ]]; then
      run_cmd systemctl enable --now hyacine-gallery-bot-telegram.service
    else
      warn "TELEGRAM_BOT_TOKEN is empty; leaving hyacine-gallery-bot-telegram disabled."
      if [[ $DRY_RUN -eq 1 ]]; then
        run_cmd systemctl disable --now hyacine-gallery-bot-telegram.service
      else
        systemctl disable --now hyacine-gallery-bot-telegram.service >/dev/null 2>&1 || true
      fi
    fi
  else
    if [[ $DRY_RUN -eq 1 ]]; then
      run_cmd systemctl disable --now hyacine-gallery-bot-telegram.service
    else
      systemctl disable --now hyacine-gallery-bot-telegram.service >/dev/null 2>&1 || true
    fi
  fi
fi

if [[ $DRY_RUN -eq 1 ]]; then
  RESULT_TITLE="Hyacine Gallery native install dry run finished."
else
  RESULT_TITLE="Hyacine Gallery native install finished."
fi

cat <<EOF

$RESULT_TITLE

App directory:  $APP_DIR
Env file:       $ENV_FILE
Data directory: $DATA_DIR

Useful commands:
  systemctl status hyacine-gallery-backend
  systemctl status hyacine-gallery-frontend
  journalctl -u hyacine-gallery-backend -f

EOF
