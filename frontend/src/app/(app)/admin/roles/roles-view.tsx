"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { PageHeader } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { catalogRows } from "@/lib/admin";
import { usePermissionCatalog, useRoles } from "@/lib/admin-queries";
import { plural } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useMyAccess } from "@/lib/queries";

import { RoleEditor } from "./role-editor";

const NEW = "new";

export function RolesView() {
  const access = useMyAccess();
  const canRead = canAnywhere(access.data, "roles:read");
  const canManage = canAnywhere(access.data, "roles:manage");
  const roles = useRoles(access.isSuccess && canRead);
  const catalog = usePermissionCatalog();

  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selected = params.get("role");
  const select = (value: string | undefined) =>
    router.replace(value ? `${pathname}?role=${value}` : pathname, { scroll: false });

  if (access.isSuccess && !canRead) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Ролі та доступ" />
        <p className="text-slate">Розділ для адміністраторів доступу.</p>
      </div>
    );
  }
  if (roles.isPending || catalog.isPending) {
    return <Skeleton className="h-64 w-full" aria-busy="true" />;
  }
  if (roles.isError || catalog.isError) {
    return <p role="alert">Не вдалося завантажити ролі.</p>;
  }

  const rows = catalogRows(catalog.data);
  const role = roles.data.find((r) => String(r.id) === selected);

  return (
    <div className="grid gap-8">
      <PageHeader title="Ролі та доступ">
        Роль — набір дозволів. Видати її можна на всю компанію або на підрозділ.
      </PageHeader>

      <div className="grid gap-8 border-t border-border pt-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-12">
        <div className="grid content-start gap-3">
          <ul className="grid gap-px">
            {roles.data.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => select(String(r.id))}
                  aria-current={String(r.id) === selected ? "true" : undefined}
                  className={cn(
                    "flex w-full items-baseline justify-between gap-3 rounded-sm px-3 py-2 text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                    String(r.id) === selected ? "bg-ink text-mist" : "hover:bg-mist",
                  )}
                >
                  <span>
                    {r.name}
                    {r.is_system && (
                      <span
                        className={cn(
                          "ml-2 text-xs",
                          String(r.id) === selected ? "text-mist/70" : "text-slate",
                        )}
                      >
                        системна
                      </span>
                    )}
                  </span>
                  <span
                    className={cn(
                      "text-xs tabular-nums",
                      String(r.id) === selected ? "text-mist/80" : "text-slate",
                    )}
                    title={`${r.users_count} ${plural(r.users_count ?? 0, ["користувач", "користувачі", "користувачів"])}`}
                  >
                    {r.users_count}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {canManage && (
            <div>
              <Button variant="outline" onClick={() => select(NEW)}>
                Нова роль
              </Button>
            </div>
          )}
        </div>

        <div className="min-w-0">
          {selected === NEW && canManage ? (
            <RoleEditor
              key={NEW}
              rows={rows}
              canManage
              onSaved={(saved) => select(String(saved.id))}
              onDeleted={() => select(undefined)}
            />
          ) : role ? (
            <RoleEditor
              key={`${role.id}-${role.permissions.join()}-${role.name}`}
              role={role}
              rows={rows}
              canManage={canManage}
              onSaved={() => undefined}
              onDeleted={() => select(undefined)}
            />
          ) : (
            <p className="text-slate">Оберіть роль, щоб побачити й налаштувати її дозволи.</p>
          )}
        </div>
      </div>
    </div>
  );
}
