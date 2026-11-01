/**
 * Права в UI — дзеркало apps/access/catalog.py: `resource:action`,
 * wildcard-и `resource:*` і `*:*`. Лише для показу/приховування елементів;
 * справжню перевірку завжди робить бекенд.
 */

export type ScopedPermissions = {
  unit: { id: number; name: string };
  permissions: string[];
};

export type Access = {
  is_superuser: boolean;
  global: string[];
  scoped: ScopedPermissions[];
};

export function matches(granted: readonly string[], codename: string) {
  const [resource] = codename.split(":");
  return (
    granted.includes(codename) || granted.includes(`${resource}:*`) || granted.includes("*:*")
  );
}

/** Дозвіл глобально або хоча б в одному підрозділі (як has_anywhere на бекенді). */
export function canAnywhere(access: Access | undefined, codename: string) {
  if (!access) return false;
  if (access.is_superuser || matches(access.global, codename)) return true;
  return access.scoped.some((scope) => matches(scope.permissions, codename));
}
