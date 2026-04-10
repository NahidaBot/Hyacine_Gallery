#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=${APP_DIR:-/opt/hyacine-gallery}
ENV_DIR=${ENV_DIR:-/etc/hyacine-gallery}
ENV_FILE=${ENV_FILE:-$ENV_DIR/hyacine-gallery.env}
DATA_DIR=${DATA_DIR:-/var/lib/hyacine-gallery}
SERVICE_USER=${SERVICE_USER:-hyacine-gallery}
SERVICE_GROUP=${SERVICE_GROUP:-hyacine-gallery}
ORIGINAL_ARGS=("$@")

REMOVE_APP=0
REMOVE_ENV=0
REMOVE_DATA=0
REMOVE_USER=0
YES=0
DRY_RUN=0

SERVICES=(
  hyacine-gallery-bot-telegram.service
  hyacine-gallery-frontend.service
  hyacine-gallery-backend.service
)

usage() {
  cat <<EOF
Uninstall Hyacine Gallery native systemd services.

By default this only stops/disables services, removes their unit files, and
runs systemctl daemon-reload. App files, env config, uploads, and the service
user are kept unless explicitly requested.

Usage:
  sudo deploy/uninstall-systemd.sh [options]

Options:
  --app-dir PATH        Application directory (default: $APP_DIR)
  --env-file PATH       Shared env file (default: $ENV_FILE)
  --data-dir PATH       Data directory (default: $DATA_DIR)
  --user NAME           Service user/group (default: $SERVICE_USER)
  --remove-app          Remove APP_DIR
  --remove-env          Remove ENV_FILE and empty ENV_DIR if possible
  --remove-data         Remove DATA_DIR, including uploads
  --remove-user         Remove service user and group
  --purge               Remove app, env, data, and service user
  --yes                 Confirm destructive removal options
  --dry-run             Print planned actions without changing the system
  -h, --help            Show this help

Environment overrides:
  APP_DIR, ENV_FILE, DATA_DIR, SERVICE_USER, SERVICE_GROUP
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
    --remove-app)
      REMOVE_APP=1
      shift
      ;;
    --remove-env)
      REMOVE_ENV=1
      shift
      ;;
    --remove-data)
      REMOVE_DATA=1
      shift
      ;;
    --remove-user)
      REMOVE_USER=1
      shift
      ;;
    --purge)
      REMOVE_APP=1
      REMOVE_ENV=1
      REMOVE_DATA=1
      REMOVE_USER=1
      shift
      ;;
    --yes)
      YES=1
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

run_cmd() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

run_cmd_allow_failure() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf ' || true\n'
  else
    "$@" >/dev/null 2>&1 || true
  fi
}

require_yes_for_destructive_options() {
  if [[ $DRY_RUN -eq 1 ]]; then
    return 0
  fi
  if [[ $YES -eq 1 ]]; then
    return 0
  fi
  if [[ $REMOVE_APP -eq 1 || $REMOVE_ENV -eq 1 || $REMOVE_DATA -eq 1 || $REMOVE_USER -eq 1 ]]; then
    cat <<EOF >&2
Refusing to remove files or users without --yes.

Requested destructive removals:
  APP_DIR:       $([[ $REMOVE_APP -eq 1 ]] && printf '%s' "$APP_DIR" || printf 'no')
  ENV_FILE:      $([[ $REMOVE_ENV -eq 1 ]] && printf '%s' "$ENV_FILE" || printf 'no')
  DATA_DIR:      $([[ $REMOVE_DATA -eq 1 ]] && printf '%s' "$DATA_DIR" || printf 'no')
  SERVICE_USER:  $([[ $REMOVE_USER -eq 1 ]] && printf '%s' "$SERVICE_USER" || printf 'no')

Rerun with --yes if this is intentional.
EOF
    exit 2
  fi
}

safe_remove_dir() {
  local path=$1
  local label=$2
  local resolved
  resolved=$(realpath -m "$path")

  case "$resolved" in
    /|/bin|/boot|/dev|/etc|/home|/lib|/lib64|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/var|/var/lib)
      die "Refusing to remove unsafe $label path: $resolved"
      ;;
  esac

  if [[ "$resolved" != /* ]]; then
    die "$label path must be absolute after resolution: $path"
  fi

  if [[ -e "$resolved" ]]; then
    run_cmd rm -rf "$resolved"
  else
    log "$label path does not exist: $resolved"
  fi
}

if [[ $DRY_RUN -eq 1 ]]; then
  warn "Dry run mode: no services, files, users, or groups will be changed."
fi

require_yes_for_destructive_options

log "Stopping and disabling systemd services"
for service in "${SERVICES[@]}"; do
  run_cmd_allow_failure systemctl disable --now "$service"
done

log "Removing systemd unit files"
for service in "${SERVICES[@]}"; do
  unit_path="/etc/systemd/system/$service"
  if [[ -e "$unit_path" || $DRY_RUN -eq 1 ]]; then
    run_cmd rm -f "$unit_path"
  else
    log "Unit file does not exist: $unit_path"
  fi
done
run_cmd systemctl daemon-reload
run_cmd_allow_failure systemctl reset-failed "${SERVICES[@]}"

if [[ $REMOVE_APP -eq 1 ]]; then
  log "Removing application directory"
  safe_remove_dir "$APP_DIR" "APP_DIR"
fi

if [[ $REMOVE_ENV -eq 1 ]]; then
  log "Removing environment file"
  if [[ -e "$ENV_FILE" || $DRY_RUN -eq 1 ]]; then
    run_cmd rm -f "$ENV_FILE"
  else
    log "Env file does not exist: $ENV_FILE"
  fi
  run_cmd_allow_failure rmdir "$ENV_DIR"
fi

if [[ $REMOVE_DATA -eq 1 ]]; then
  log "Removing data directory"
  safe_remove_dir "$DATA_DIR" "DATA_DIR"
fi

if [[ $REMOVE_USER -eq 1 ]]; then
  log "Removing service user and group"
  if id "$SERVICE_USER" >/dev/null 2>&1 || [[ $DRY_RUN -eq 1 ]]; then
    run_cmd_allow_failure userdel "$SERVICE_USER"
  else
    log "User does not exist: $SERVICE_USER"
  fi
  if getent group "$SERVICE_GROUP" >/dev/null 2>&1 || [[ $DRY_RUN -eq 1 ]]; then
    run_cmd_allow_failure groupdel "$SERVICE_GROUP"
  else
    log "Group does not exist: $SERVICE_GROUP"
  fi
fi

if [[ $DRY_RUN -eq 1 ]]; then
  RESULT_TITLE="Hyacine Gallery native uninstall dry run finished."
else
  RESULT_TITLE="Hyacine Gallery native uninstall finished."
fi

app_status="kept"
env_status="kept"
data_status="kept"
user_status="kept"
[[ $REMOVE_APP -eq 1 ]] && app_status="removed"
[[ $REMOVE_ENV -eq 1 ]] && env_status="removed"
[[ $REMOVE_DATA -eq 1 ]] && data_status="removed"
[[ $REMOVE_USER -eq 1 ]] && user_status="removed"
if [[ $DRY_RUN -eq 1 ]]; then
  [[ $REMOVE_APP -eq 1 ]] && app_status="would remove"
  [[ $REMOVE_ENV -eq 1 ]] && env_status="would remove"
  [[ $REMOVE_DATA -eq 1 ]] && data_status="would remove"
  [[ $REMOVE_USER -eq 1 ]] && user_status="would remove"
fi

cat <<EOF

$RESULT_TITLE

Removed systemd units:
  ${SERVICES[0]}
  ${SERVICES[1]}
  ${SERVICES[2]}

Local resources:
  App directory:  $APP_DIR ($app_status)
  Env file:       $ENV_FILE ($env_status)
  Data directory: $DATA_DIR ($data_status)
  Service user:   $SERVICE_USER ($user_status)

For full removal:
  sudo deploy/uninstall-systemd.sh --purge --yes

EOF
