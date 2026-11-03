#!/bin/bash
# Один раз на сервері: щоденні Slack-нагадування (manage.py slack_reminders).
#   09:30 пн–пт — тим, хто розглядає відпустки: скільки заявок чекає
#   11:00 пн–пт — працівникам, які ще не відмітились у табелі (у свята — ні)
# Час — сервера; перевірте `timedatectl` (очікується Europe/Kyiv) або змініть
# години нижче. Повторний запуск скрипта замінює записи, а не дублює.
# Без SLACK_BOT_TOKEN у .env команда нічого не надсилає.
set -euo pipefail

app_dir="${APP_DIR:-/www/hrm}"
log="${BACKUP_DIR:-/www/hrm-backups}/reminders.log"
marker="# hrm slack reminders"
run="cd $app_dir && docker compose -f docker-compose.server.yml exec -T api python manage.py slack_reminders"

mkdir -p "$(dirname "$log")"
{
  crontab -l 2>/dev/null | grep -vF "$marker" || true
  echo "30 9 * * 1-5 $run --vacations >> $log 2>&1 $marker"
  echo "0 11 * * 1-5 $run --attendance >> $log 2>&1 $marker"
} | crontab -
crontab -l | grep -F "$marker"
