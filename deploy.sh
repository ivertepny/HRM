#!/bin/bash
# Деплой на VPS. Запускає GitHub Actions по SSH (.github/workflows/deploy.yml):
# логін-шел користувача деплою — диспетчер, він за назвою репозиторію (HRM)
# викликає `bash /www/hrm/deploy.sh`. Вручну — так само.
#
# Тіло — у функції: bash дочитує скрипт під час виконання, а git reset
# нижче може його замінити. Функцію bash розбирає цілком до запуску.
set -euo pipefail

main() {
  local app_dir="${APP_DIR:-/www/hrm}"
  local compose=(docker compose -f docker-compose.server.yml)
  cd "$app_dir"

  echo "=== git: origin/main ==="
  git fetch --quiet origin main
  git reset --hard origin/main
  # Ігноровані файли (.env) лишаються: -x не передаємо
  git clean -fd
  # docker-compose.server.yml передає його в api як SENTRY_RELEASE
  export GIT_COMMIT_SHA
  GIT_COMMIT_SHA="$(git rev-parse HEAD)"
  echo "commit: $GIT_COMMIT_SHA"

  echo "=== бекап перед деплоєм ==="
  if docker ps --format '{{.Names}}' | grep -qx hrm-db; then
    BACKUP_OFFSITE=0 bash scripts/backup.sh
  else
    echo "hrm-db не запущено (перший деплой?) — пропускаю"
  fi

  echo "=== збірка і запуск ==="
  # --wait: чекає healthcheck усіх сервісів; нездоровий стек — деплой падає
  "${compose[@]}" up -d --build --remove-orphans --wait --wait-timeout 300

  echo "=== прибирання старих образів ==="
  docker image prune -f >/dev/null

  "${compose[@]}" ps
  echo "=== готово ==="
}

main "$@"
