import { canAnywhere, type Access } from "./access";

export type NavItem = {
  href: string;
  label: string;
  /** Без permission пункт видно всім (власні дані доступні завжди). */
  permission?: string;
  /** Розділ ще не реалізований — показуємо, але не даємо перейти. */
  soon?: boolean;
};

export type NavGroup = { label: string; items: NavItem[] };

export const NAVIGATION: NavGroup[] = [
  {
    label: "Я",
    items: [
      { href: "/profile", label: "Мій профіль" },
      { href: "/vacations", label: "Мої відпустки" },
      { href: "/attendance", label: "Мій табель", permission: "attendance:write" },
      { href: "/assistant", label: "AI-асистент", permission: "ai:use" },
    ],
  },
  {
    label: "Команда",
    items: [
      { href: "/employees", label: "Працівники", permission: "employees:read" },
      {
        href: "/vacations/review",
        label: "Відпустки команди",
        permission: "vacations:manage",
      },
      { href: "/attendance/report", label: "Табель команди", permission: "attendance:read" },
    ],
  },
  {
    label: "Компанія",
    items: [
      { href: "/company", label: "Оргструктура", permission: "company:read" },
      { href: "/equipment", label: "Обладнання", permission: "equipment:read" },
    ],
  },
  {
    label: "Адміністрування",
    items: [
      { href: "/admin/users", label: "Облікові записи", permission: "users:read" },
      { href: "/admin/roles", label: "Ролі та доступ", permission: "roles:read" },
    ],
  },
];

/** Активний пункт — з найдовшим href, що є префіксом шляху
 *  (/vacations/review підсвічує «Відпустки команди», а не «Мої відпустки»). */
export function activeHref(pathname: string, groups = NAVIGATION) {
  return groups
    .flatMap((group) => group.items.map((item) => item.href))
    .filter((href) => pathname === href || pathname.startsWith(`${href}/`))
    .sort((a, b) => b.length - a.length)[0];
}

/** Лише доступні пункти; групи без пунктів зникають. */
export function visibleNavigation(access: Access | undefined, groups = NAVIGATION) {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.permission || canAnywhere(access, item.permission),
      ),
    }))
    .filter((group) => group.items.length > 0);
}
