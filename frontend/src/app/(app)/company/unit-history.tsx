"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { FIELD_LABELS, HISTORY_LABELS } from "@/lib/org";
import { useUnitHistory } from "@/lib/queries";

const dateTime = new Intl.DateTimeFormat("uk-UA", { dateStyle: "long", timeStyle: "short" });

type Change = { field: string; old: unknown; new: unknown };

function describe(change: Change) {
  const label = FIELD_LABELS[change.field] ?? change.field;
  if (change.field === "parent") return `перенесено (${label})`;
  return `${label}: «${change.old ?? "—"}» → «${change.new ?? "—"}»`;
}

export function UnitHistory({ unitId }: { unitId: number }) {
  const history = useUnitHistory(unitId);

  if (history.isPending) return <Skeleton className="h-24 w-full" />;
  if (history.isError) {
    return <p role="alert">Не вдалося завантажити історію: {history.error.message}</p>;
  }
  if (history.data.length === 0) return <p className="text-slate">Змін ще не було.</p>;

  return (
    <ol className="grid gap-4">
      {history.data.map((record, i) => {
        const changes = (record.changes ?? []) as Change[];
        return (
          <li key={`${record.history_date}-${i}`}>
            <p>
              <span className="font-medium">
                {HISTORY_LABELS[record.event_type ?? ""] ?? record.event_type}
              </span>
              <span className="text-slate">
                {" — "}
                {dateTime.format(new Date(record.history_date))}, {record.history_user}
              </span>
            </p>
            {changes.length > 0 && (
              <p className="mt-1 text-sm">{changes.map(describe).join("; ")}</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
