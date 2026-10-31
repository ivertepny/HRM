# ===========================================================================
# HRM-NEW — dev.ps1  (Windows PowerShell)
# Використання: .\dev.ps1 <команда>
# Приклад:      .\dev.ps1 install
# ===========================================================================

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "HRM-NEW dev tasks" -ForegroundColor Cyan
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  .\dev.ps1 install        " -NoNewline; Write-Host "Встановити залежності (uv sync)" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 lint           " -NoNewline; Write-Host "Перевірити код (ruff check)" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 fmt            " -NoNewline; Write-Host "Відформатувати код (ruff format)" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 fix            " -NoNewline; Write-Host "Виправити + відформатувати" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 check          " -NoNewline; Write-Host "Lint + перевірка форматування" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 migrate        " -NoNewline; Write-Host "python manage.py migrate" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 makemigrations " -NoNewline; Write-Host "python manage.py makemigrations" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 seed           " -NoNewline; Write-Host "Синхронізувати дозволи і системні ролі" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 run            " -NoNewline; Write-Host "Запустити dev-сервер (0.0.0.0:8000)" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 shell          " -NoNewline; Write-Host "Django shell" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 test           " -NoNewline; Write-Host "Запустити тести" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 test-cov       " -NoNewline; Write-Host "Тести з coverage (HTML-звіт)" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 docker-up      " -NoNewline; Write-Host "docker compose up --build -d" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 docker-down    " -NoNewline; Write-Host "docker compose down" -ForegroundColor Gray
    Write-Host "  .\dev.ps1 docker-logs    " -NoNewline; Write-Host "Логи контейнера api" -ForegroundColor Gray
    Write-Host ""
}

switch ($Command) {
    "install" {
        Write-Host "▶ uv sync --group dev" -ForegroundColor Cyan
        uv sync --group dev
    }
    "lint" {
        Write-Host "▶ ruff check ." -ForegroundColor Cyan
        uv run ruff check .
    }
    "fmt" {
        Write-Host "▶ ruff format ." -ForegroundColor Cyan
        uv run ruff format .
    }
    "fix" {
        Write-Host "▶ ruff check --fix . && ruff format ." -ForegroundColor Cyan
        uv run ruff check --fix .
        uv run ruff format .
    }
    "check" {
        Write-Host "▶ ruff check . && ruff format --check ." -ForegroundColor Cyan
        uv run ruff check .
        if ($LASTEXITCODE -eq 0) {
            uv run ruff format --check .
        }
    }
    "migrate" {
        Write-Host "▶ python manage.py migrate" -ForegroundColor Cyan
        uv run python manage.py migrate
    }
    "makemigrations" {
        Write-Host "▶ python manage.py makemigrations" -ForegroundColor Cyan
        uv run python manage.py makemigrations
    }
    "seed" {
        Write-Host "▶ python manage.py seed_roles" -ForegroundColor Cyan
        uv run python manage.py seed_roles
    }
    "run" {
        Write-Host "▶ python manage.py runserver 0.0.0.0:8000" -ForegroundColor Cyan
        uv run python manage.py runserver 0.0.0.0:8000
    }
    "shell" {
        Write-Host "▶ python manage.py shell" -ForegroundColor Cyan
        uv run python manage.py shell
    }
    "test" {
        Write-Host "▶ pytest" -ForegroundColor Cyan
        uv run pytest
    }
    "test-cov" {
        Write-Host "▶ pytest --cov --cov-report=html" -ForegroundColor Cyan
        uv run pytest --cov --cov-report=html
    }
    "docker-up" {
        Write-Host "▶ docker compose up --build -d" -ForegroundColor Cyan
        docker compose up --build -d
    }
    "docker-down" {
        Write-Host "▶ docker compose down" -ForegroundColor Cyan
        docker compose down
    }
    "docker-logs" {
        Write-Host "▶ docker compose logs -f api" -ForegroundColor Cyan
        docker compose logs -f api
    }
    default {
        Show-Help
    }
}

