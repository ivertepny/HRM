"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { PEOPLE, plural, UNITS } from "@/lib/format";
import { buildTree, findNode, subtreeEmployees } from "@/lib/org";
import { useMyAccess, useUnitTree } from "@/lib/queries";

import { OrgTree } from "./org-tree";
import { UnitDetails } from "./unit-details";
import { UnitForm } from "./unit-form";

export function OrgView() {
  const access = useMyAccess();
  const can = (codename: string) => canAnywhere(access.data, codename);
  const canRead = can("company:read");
  const tree = useUnitTree(access.isSuccess && canRead);

  // Вибраний підрозділ — у URL (?unit=), щоб посиланням можна було поділитись
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selectedId = params.get("unit") ? Number(params.get("unit")) : undefined;

  const units = useMemo(() => tree.data ?? [], [tree.data]);
  const roots = useMemo(() => buildTree(units), [units]);
  const types = useMemo(
    () => [...new Set(units.map((u) => u.custom_type).filter(Boolean) as string[])].sort(),
    [units],
  );

  // Розгорнуті корені (видно два рівні) і шлях до вибраного; решта — за кліком
  const [toggled, setToggled] = useState<Map<number, boolean>>(new Map());
  const expanded = useMemo(() => {
    const set = new Set<number>();
    for (const unit of units) {
      const depth = unit.ancestors?.length ?? 0;
      const opened = toggled.get(unit.id!);
      if (opened ?? depth < 1) set.add(unit.id!);
    }
    const selected = units.find((u) => u.id === selectedId);
    for (const ancestor of selected?.ancestors ?? []) {
      if (toggled.get(ancestor.id) !== false) set.add(ancestor.id);
    }
    return set;
  }, [units, toggled, selectedId]);

  const [creatingRoot, setCreatingRoot] = useState(false);

  function select(id: number | undefined) {
    const next = new URLSearchParams(params);
    if (id === undefined) next.delete("unit");
    else next.set("unit", String(id));
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  }

  if (access.isSuccess && !canRead) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Оргструктура" />
        <p className="text-slate">Перегляд оргструктури доступний з дозволом на неї — зверніться до HR.</p>
      </div>
    );
  }
  if (tree.isPending) {
    return (
      <div className="grid gap-6" aria-busy="true">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (tree.isError) {
    return <p role="alert">Не вдалося завантажити оргструктуру: {tree.error.message}</p>;
  }

  const selected = selectedId !== undefined ? findNode(roots, selectedId) : undefined;
  const people = roots.reduce((sum, root) => sum + subtreeEmployees(root), 0);
  const canWrite = can("company:write");

  return (
    <div className="grid gap-8">
      <PageHeader title="Оргструктура">
        {units.length > 0 &&
          `${units.length} ${plural(units.length, UNITS)}, ${people} ${plural(people, PEOPLE)}.`}
      </PageHeader>

      {units.length === 0 ? (
        <div className="grid gap-4">
          <p className="text-slate">
            Підрозділів ще немає.{canWrite && " Почніть з верхнього рівня — головного офісу чи компанії."}
          </p>
          {canWrite &&
            (creatingRoot ? (
              <UnitForm
                parents={[]}
                types={types}
                onDone={(created) => {
                  setCreatingRoot(false);
                  select(created.id);
                }}
                onCancel={() => setCreatingRoot(false)}
              />
            ) : (
              <div>
                <Button onClick={() => setCreatingRoot(true)}>Створити підрозділ</Button>
              </div>
            ))}
        </div>
      ) : (
        <div className="grid gap-8 border-t border-border pt-6 lg:grid-cols-[20rem_minmax(0,1fr)] lg:gap-12">
          <div className="lg:sticky lg:top-6 lg:max-h-[calc(100dvh-8rem)] lg:self-start lg:overflow-y-auto">
            <OrgTree
              nodes={roots}
              selectedId={selectedId}
              expanded={expanded}
              onToggle={(id) =>
                setToggled((prev) => new Map(prev).set(id, !expanded.has(id)))
              }
              onSelect={select}
            />
          </div>
          <div className="min-w-0">
            {selected ? (
              <UnitDetails
                key={selected.id}
                node={selected}
                allUnits={units}
                types={types}
                can={{
                  write: canWrite,
                  remove: can("company:delete"),
                  employees: can("employees:read"),
                }}
                onSelect={select}
              />
            ) : (
              <p className="text-slate">
                Оберіть підрозділ у дереві, щоб побачити працівників, діаграму та історію змін.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
