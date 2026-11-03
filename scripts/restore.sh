#!/bin/bash
# Відновлення БД (і, за бажанням, файлів) з бекапу scripts/backup.sh.
# РУЙНІВНО: поточна база (і файли) замінюються.
#
#   bash scripts/restore.sh /www/hrm-backups/db_2026-11-03_03-00.sql.gz [media_….tar.gz]
set -euo pipefail

if [ $# -lt 1 ] || [ ! -f "$1" ]; then
  echo "Використання: $0 <db_….sql.gz> [media_….tar.gz]"
  ls -lh "${BACKUP_DIR:-/www/hrm-backups}" 2>/dev/null || true
  exit 1
fi
db_file="$1"
media_file="${2:-}"
compose=(docker compose -f docker-compose.server.yml)
cd "${APP_DIR:-/www/hrm}"

echo "УВАГА: база буде замінена даними з $db_file${media_file:+, файли — з $media_file}."
read -r -p "Введіть 'restore', щоб продовжити: " answer
[ "$answer" = "restore" ] || { echo "Скасовано."; exit 1; }

# Застосунок зупиняємо, щоб ніхто не писав у базу під час відновлення
"${compose[@]}" stop nginx frontend api

docker exec hrm-db sh -c '
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE);" \
    -c "CREATE DATABASE \"$POSTGRES_DB\";"'
# stdout — результати SELECT setval(...) з дампу, не потрібні; помилки — у stderr
gunzip -c "$db_file" | docker exec -i hrm-db sh -c \
  'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /dev/null
echo "БД відновлено."

if [ -n "$media_file" ]; then
  # Volume media монтується в тимчасовий контейнер з образу api
  "${compose[@]}" run --rm --no-deps -T --user root --entrypoint sh api \
    -c 'find /usr/src/media -mindepth 1 -delete && tar -xzf - -C /usr/src/media && chown -R app:app /usr/src/media' \
    < "$media_file"
  echo "Файли відновлено."
fi

"${compose[@]}" up -d --wait
echo "Готово."
