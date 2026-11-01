"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { EVENT_LABELS } from "@/lib/employees";
import { formatDate, formatMoney, LEVEL_LABELS } from "@/lib/format";
import { useCareerHistory } from "@/lib/queries";

/** Кадровий журнал — справді послідовність подій, тому показуємо як стрічку часу. */
export function CareerLog({ employeeId }: { employeeId: number }) {
  const history = useCareerHistory(employeeId);

  if (history.isPending) return <Skeleton className="h-32 w-full" />;
  if (history.isError) {
    return <p role="alert">Не вдалося завантажити журнал: {history.error.message}</p>;
  }
  if (history.data.length === 0) return <p className="text-slate">Подій ще немає.</p>;

  return (
    <ol className="grid gap-0 border-l-2 border-border">
      {history.data.map((record) => {
        const details = [
          record.position?.name,
          record.structural_unit?.full_name,
          record.level ? LEVEL_LABELS[record.level] : null,
          "salary" in record ? formatMoney(record.salary, record.salary_currency) : null,
        ].filter(Boolean);
        return (
          <li key={record.id} className="relative pb-6 pl-5 last:pb-0">
            <span
              aria-hidden
              className={`absolute top-1.5 -left-[7px] size-3 rounded-full border-2 border-sheet ${
                record.event === "fired" ? "bg-destructive" : record.event === "hired" ? "bg-primary" : "bg-ink"
              }`}
            />
            <p>
              <span className="font-medium">{EVENT_LABELS[record.event!]}</span>
              <span className="text-slate"> — з {formatDate(record.date)}</span>
            </p>
            <p className="mt-1 text-sm">{details.join("; ")}</p>
            {record.reason && <p className="mt-1 text-sm text-slate">«{record.reason}»</p>}
            {record.changed_by && (
              <p className="mt-1 text-xs text-slate">Вніс(-ла): {record.changed_by}</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
