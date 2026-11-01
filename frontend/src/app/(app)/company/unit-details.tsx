"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import type { Unit } from "@/lib/employees";
import { PEOPLE, plural } from "@/lib/format";
import { subtreeEmployees, subtreeIds, type UnitNode } from "@/lib/org";
import { useCloseUnit } from "@/lib/queries";

import { UnitForm } from "./unit-form";
import { UnitHistory } from "./unit-history";

type Mode = "view" | "add" | "edit" | "close";

type Props = {
  node: UnitNode;
  allUnits: Unit[];
  types: string[];
  can: { write: boolean; remove: boolean; employees: boolean };
  onSelect: (id: number | undefined) => void;
};

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3 border-t border-border pt-6">
      <h3 className="font-sans text-[0.9375rem] font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export function UnitDetails({ node, allUnits, types, can, onSelect }: Props) {
  const [mode, setMode] = useState<Mode>("view");
  const [diagramFailed, setDiagramFailed] = useState(false);
  const close = useCloseUnit();

  const total = subtreeEmployees(node);
  const blocked = subtreeIds(node);
  const parentsForEdit = allUnits.filter((u) => !blocked.has(u.id!));
  const descendants = blocked.size - 1;
  const path = (node.ancestors ?? []).map((a) => a.name).join(" > ");

  async function confirmClose() {
    // mutateAsync, а не колбеки mutate: після оновлення дерева ця панель
    // розмонтовується, і колбеки конкретного виклику вже не спрацювали б
    try {
      await close.mutateAsync(node.id!);
    } catch (error) {
      toast.error((error as Error).message);
      return;
    }
    toast.success(`Підрозділ «${node.name}» закрито`);
    onSelect(node.parent ?? undefined);
  }

  return (
    <div className="grid gap-8">
      <header>
        {node.custom_type && <p className="text-sm text-slate">{node.custom_type}</p>}
        <h2 className="text-[1.75rem] leading-tight font-medium md:text-[2.25rem]">{node.name}</h2>
        {path && <p className="mt-1 text-slate">{path}</p>}
      </header>

      <dl className="grid grid-cols-3 gap-4 sm:max-w-lg">
        {[
          ["Працює тут", node.employees_count ?? 0],
          ["З дочірніми", total],
          ["Дочірніх підрозділів", node.children.length],
        ].map(([label, value]) => (
          <div key={label}>
            <dd className="font-heading text-[1.75rem] font-medium tabular-nums">{value}</dd>
            <dt className="text-sm text-slate">{label}</dt>
          </div>
        ))}
      </dl>

      {(can.employees || can.write || can.remove) && mode === "view" && (
        <div className="flex flex-wrap gap-2">
          {can.employees && total > 0 && (
            <Link
              href={`/employees?unit=${node.id}`}
              className={buttonVariants({ variant: "outline" })}
            >
              Переглянути працівників
            </Link>
          )}
          {can.write && (
            <>
              <Button variant="outline" onClick={() => setMode("add")}>
                Додати дочірній підрозділ
              </Button>
              <Button variant="outline" onClick={() => setMode("edit")}>
                Редагувати
              </Button>
            </>
          )}
          {can.remove && (
            <Button variant="ghost" onClick={() => setMode("close")}>
              Закрити підрозділ
            </Button>
          )}
        </div>
      )}

      {mode === "add" && (
        <UnitForm
          parentId={node.id}
          parents={allUnits}
          types={types}
          onDone={(created) => {
            setMode("view");
            onSelect(created.id);
          }}
          onCancel={() => setMode("view")}
        />
      )}
      {mode === "edit" && (
        <UnitForm
          unit={node}
          parents={parentsForEdit}
          types={types}
          onDone={() => setMode("view")}
          onCancel={() => setMode("view")}
        />
      )}
      {mode === "close" && (
        <div className="grid max-w-xl gap-3 rounded-md bg-mist p-4">
          {total > 0 ? (
            <p>
              У підрозділі{descendants > 0 && " та дочірніх"} {total}{" "}
              {plural(total, PEOPLE)}. Спершу переведіть їх в інші підрозділи — після цього
              підрозділ можна буде закрити.
            </p>
          ) : (
            <p>
              Підрозділ «{node.name}»
              {descendants > 0 &&
                ` і ${descendants} ${plural(descendants, ["дочірній", "дочірні", "дочірніх"])}`}{" "}
              {descendants > 0 ? "зникнуть" : "зникне"} з оргструктури.
              Історія змін збережеться.
            </p>
          )}
          <span className="flex gap-2">
            {total === 0 && (
              <Button variant="destructive" disabled={close.isPending} onClick={confirmClose}>
                {close.isPending ? "Закриваємо…" : "Закрити підрозділ"}
              </Button>
            )}
            <Button variant="ghost" onClick={() => setMode("view")}>
              {total > 0 ? "Зрозуміло" : "Не закривати"}
            </Button>
          </span>
        </div>
      )}

      <Block title="Діаграма">
        {diagramFailed ? (
          <p className="text-slate">
            Діаграма зараз недоступна — на сервері не налаштовано Graphviz.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border bg-sheet p-3">
            {/* SVG як <img>: браузер не виконує скриптів усередині */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={`${node.id}-${node.name}-${node.children.length}`}
              src={`/api/backend/api/company/units/${node.id}/diagram/`}
              alt={`Діаграма підрозділу «${node.name}» і дочірніх`}
              className="max-w-none"
              onError={() => setDiagramFailed(true)}
            />
          </div>
        )}
      </Block>

      <Block title="Історія змін">
        <UnitHistory unitId={node.id!} />
      </Block>
    </div>
  );
}
