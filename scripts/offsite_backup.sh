#!/bin/bash
# Копія локальних бекапів (/www/hrm-backups) поза сервером — restic у Docker
# на Hetzner Storage Box. Викликає scripts/backup.sh після кожного бекапу.
#
# restic шифрує дані до відправки (у бекапах — персональні дані), дедуплікує
# (щоденний архів файлів не множить обсяг) і сам веде ротацію. Стерті на
# сервері файли не зникають з копії (це не rsync --delete). Але ключ дає
# повний доступ до репозиторію, тож від зловмисника на сервері захищають лише
# snapshots Storage Box — увімкніть їх.
#
# Налаштування — у $RESTIC_DIR (поза репозиторієм, chmod 700), див. docs/deploy.md:
#   restic.env     RESTIC_REPOSITORY, RESTIC_PASSWORD, SFTP_COMMAND
#   id_ed25519     ключ до Storage Box
#   known_hosts    ключ хоста Storage Box
# Немає restic.env — копіювання вимкнено (скрипт нічого не робить).
#
#   bash scripts/offsite_backup.sh            бекап + ротація
#   bash scripts/offsite_backup.sh init       один раз: створити репозиторій
#   bash scripts/offsite_backup.sh <команда>  будь-яка команда restic, напр. snapshots
#   RESTORE_DIR=/tmp/r bash scripts/offsite_backup.sh restore latest --target /restore
set -euo pipefail

RESTIC_DIR="${RESTIC_DIR:-/www/hrm-restic}"
BACKUP_DIR="${BACKUP_DIR:-/www/hrm-backups}"
RESTIC_IMAGE="restic/restic:0.18.1"
log() { echo "[$(date '+%F %T')] $*"; }

if [ ! -f "$RESTIC_DIR/restic.env" ]; then
  log "off-site: $RESTIC_DIR/restic.env немає — пропускаю"
  exit 0
fi
# shellcheck source=/dev/null
. "$RESTIC_DIR/restic.env"
: "${RESTIC_REPOSITORY:?задайте RESTIC_REPOSITORY у restic.env}"
: "${RESTIC_PASSWORD:?задайте RESTIC_PASSWORD у restic.env}"
export RESTIC_REPOSITORY RESTIC_PASSWORD

restic() {
  local options=() mounts=()
  if [ -n "${SFTP_COMMAND:-}" ]; then options+=(-o "sftp.command=$SFTP_COMMAND"); fi
  # Куди відновлювати — лише коли попросили (restore … --target /restore)
  if [ -n "${RESTORE_DIR:-}" ]; then mounts+=(-v "$RESTORE_DIR:/restore"); fi
  # --hostname: стабільне ім'я хоста в снапшотах (інакше — id контейнера)
  docker run --rm -i --hostname hrm \
    -e RESTIC_REPOSITORY -e RESTIC_PASSWORD \
    -v "$BACKUP_DIR:/backups:ro" \
    -v "$RESTIC_DIR:/restic:ro" \
    "${mounts[@]}" \
    -v hrm-restic-cache:/root/.cache/restic \
    "$RESTIC_IMAGE" "${options[@]}" "$@"
}

if [ $# -gt 0 ]; then
  restic "$@"
  exit
fi

log "off-site: backup → $RESTIC_REPOSITORY"
restic backup /backups --tag hrm --exclude /backups/backup.log --quiet
log "off-site: ротація"
restic forget --tag hrm --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune --quiet
# Цілісність метаданих щоразу; вибірка самих даних — раз на тиждень (неділя)
if [ "$(date +%u)" = 7 ]; then
  restic check --read-data-subset=10% --quiet
else
  restic check --quiet
fi
log "off-site: OK"
