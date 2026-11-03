#!/bin/bash
# Бекап БД (pg_dump) і файлів працівників (volume media) з ротацією.
# Запускають deploy.sh (перед кожним деплоєм) і cron (scripts/setup_backup_cron.sh).
#
# Бекапи — поза репозиторієм: deploy.sh робить git clean. У них персональні
# дані працівників, тож файли доступні лише власнику (umask 077).
set -euo pipefail
umask 077

BACKUP_DIR="${BACKUP_DIR:-/www/hrm-backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
stamp="$(date +%Y-%m-%d_%H-%M)"
log() { echo "[$(date '+%F %T')] $*"; }

mkdir -p "$BACKUP_DIR"

db_file="$BACKUP_DIR/db_$stamp.sql.gz"
log "БД → $db_file"
# Змінні POSTGRES_* беруться з оточення контейнера, не з .env на хості
docker exec hrm-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
  | gzip > "$db_file.tmp"
mv "$db_file.tmp" "$db_file"

media_file="$BACKUP_DIR/media_$stamp.tar.gz"
log "файли → $media_file"
docker exec hrm-api tar -czf - -C /usr/src/media . > "$media_file.tmp"
mv "$media_file.tmp" "$media_file"

log "розмір: $(du -h "$db_file" | cut -f1) БД, $(du -h "$media_file" | cut -f1) файли"

removed=$(find "$BACKUP_DIR" -maxdepth 1 \( -name 'db_*.sql.gz' -o -name 'media_*.tar.gz' \) \
  -mtime +"$KEEP_DAYS" -print -delete | wc -l)
log "ротація: видалено $removed старших за $KEEP_DAYS дн."
