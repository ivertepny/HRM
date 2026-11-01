"""Каталог дозволів і системних ролей — джерело правди для `manage.py seed_roles`.

Дозвіл — рядок `resource:action`. Роль може містити wildcard-и:
`resource:*` (усі дії над ресурсом) і `*:*` (усе).
"""

WILDCARD = "*"

# resource -> {action: опис}
PERMISSION_CATALOG = {
    "users": {
        "read": "Перегляд облікових записів",
        "write": "Створення і редагування облікових записів",
        "delete": "Видалення облікових записів",
    },
    "employees": {
        "read": "Перегляд профілів працівників",
        "write": "Прийом, переведення, зміна профілю, звільнення",
        "delete": "Видалення профілів працівників",
    },
    "salary": {
        "read": "Перегляд зарплат",
        "write": "Зміна зарплат",
    },
    "documents": {
        "read": "Перегляд документів працівників",
        "write": "Завантаження документів",
        "delete": "Видалення документів",
    },
    "company": {
        "read": "Перегляд організаційної структури",
        "write": "Створення і редагування підрозділів",
        "delete": "Закриття підрозділів",
    },
    "roles": {
        "read": "Перегляд ролей і призначень",
        "manage": "Керування ролями і призначення ролей",
    },
    "ai": {
        "use": "Користування AI-асистентом",
    },
    "vacations": {
        "read": "Перегляд відпусток",
        "write": "Подання заявок на відпустку",
        "manage": "Схвалення і відхилення відпусток",
    },
    "equipment": {
        "read": "Перегляд обладнання",
        "manage": "Облік і видача обладнання",
    },
    "attendance": {
        "read": "Перегляд табеля і місячного звіту",
        "write": "Відмітка власної присутності",
    },
}

SYSTEM_ROLES = {
    "System Admin": {
        "description": "Повний доступ до системи",
        "permissions": ["*:*"],
    },
    "HR Manager": {
        "description": "Кадрові операції, зарплати, відпустки, обладнання",
        "permissions": [
            "employees:*",
            "salary:*",
            "documents:*",
            "users:read",
            "company:read",
            "vacations:read",
            "vacations:write",
            "vacations:manage",
            "equipment:read",
            "equipment:manage",
            "attendance:read",
            "ai:use",
        ],
    },
    # Власні дані (профіль, зарплата, кар'єрна історія, документи) доступні
    # завжди, без дозволів — тому salary:read тут немає: він відкрив би чужі.
    "Employee": {
        "description": "Базовий доступ працівника",
        "permissions": [
            "employees:read",
            "company:read",
            "vacations:write",
            "attendance:write",
            "ai:use",
        ],
    },
}

DEFAULT_ROLE = "Employee"  # видається кожному новому користувачу


def all_codenames():
    """Усі дозволи каталогу разом з wildcard-ами (`resource:*`, `*:*`)."""
    codenames = [f"{WILDCARD}:{WILDCARD}"]
    for resource, actions in PERMISSION_CATALOG.items():
        codenames.append(f"{resource}:{WILDCARD}")
        codenames.extend(f"{resource}:{action}" for action in actions)
    return codenames


def describe(codename):
    resource, action = codename.split(":")
    if resource == WILDCARD:
        return "Усі дозволи"
    if action == WILDCARD:
        return f"Усі дії: {resource}"
    return PERMISSION_CATALOG[resource][action]


def matches(granted, codename):
    """Чи покриває набір наданих дозволів (з wildcard-ами) потрібний дозвіл."""
    resource, _ = codename.split(":")
    return (
        codename in granted
        or f"{resource}:{WILDCARD}" in granted
        or f"{WILDCARD}:{WILDCARD}" in granted
    )
