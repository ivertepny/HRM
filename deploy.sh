#!/bin/bash
# Деплой на VPS. Запускає GitHub Actions по SSH (deploy-ssh.yml) — ключ у
# authorized_keys обмежений командою `bash /www/hrm/deploy.sh`; вручну — так само.
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
  echo "commit: $(git rev-parse --short HEAD)"

  echo "=== бекап перед деплоєм ==="
  if docker ps --format '{{.Names}}' | grep -qx hrm-db; then
    bash scripts/backup.sh
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
