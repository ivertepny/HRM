#!/bin/bash
# Один раз на сервері: щоденний бекап о 03:00 (час сервера). Повторний запуск
# замінює запис, а не дублює.
set -euo pipefail

app_dir="${APP_DIR:-/www/hrm}"
backup_dir="${BACKUP_DIR:-/www/hrm-backups}"
marker="# hrm backup"
# BACKUP_PING_URL (необов'язково) — URL моніторингу, напр. healthchecks.io
ping="${BACKUP_PING_URL:+BACKUP_PING_URL=$BACKUP_PING_URL }"
line="0 3 * * * ${ping}bash $app_dir/scripts/backup.sh >> $backup_dir/backup.log 2>&1 $marker"

mkdir -p "$backup_dir"
{ crontab -l 2>/dev/null | grep -vF "$marker" || true; echo "$line"; } | crontab -
crontab -l | grep -F "$marker"
