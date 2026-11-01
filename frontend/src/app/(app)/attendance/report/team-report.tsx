"use client";

import { useState } from "react";

import { MonthSwitcher } from "@/components/app/month-switcher";
import { NativeSelect } from "@/components/app/native-select";
import { PageHeader } from "@/components/app/section";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { formatHours, monthOf } from "@/lib/attendance";
import { unitPath } from "@/lib/employees";
import { useAttendanceReport, useMyAccess, useUnits } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

const COLUMNS = [
  ["office", "Офіс"],
  ["remote", "Віддалено"],
  ["off", "Не працював"],
  ["vacation", "Відпустка"],
  ["missing", "Без відмітки"],
] as const;

export function TeamReport() {
  const access = useMyAccess();
  const allowed = canAnywhere(access.data, "attendance:read");
  const units = useUnits(allowed && canAnywhere(access.data, "company:read"));
  const thisMonth = monthOf(todayISO());
  const [month, setMonth] = useState(thisMonth);
  const [unit, setUnit] = useState("");
  const report = useAttendanceReport(month, unit ? Number(unit) : undefined);

  if (access.isSuccess && !allowed) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Табель команди" />
        <p className="text-slate">Розділ для HR і керівників із доступом до табеля.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-8">
      <PageHeader title="Табель команди">
        {report.data &&
          `Робочих днів у місяці: ${report.data.working_days}. Пропуски рахуються до сьогодні, без днів відпустки.`}
      </PageHeader>

      <div className="flex flex-wrap items-end justify-between gap-4 border-t border-border pt-6">
        <MonthSwitcher month={month} max={thisMonth} onChange={setMonth} />
        {units.data && (
          <div className="grid w-full gap-2 sm:w-80">
            <Label htmlFor="report-unit">Підрозділ</Label>
            <NativeSelect id="report-unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
              <option value="">Уся область доступу</option>
              {units.data.map((u) => (
                <option key={u.id} value={u.id}>
                  {unitPath(u)}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
      </div>

      {report.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : report.isError ? (
        <p role="alert">Не вдалося завантажити звіт: {report.error.message}</p>
      ) : report.data.rows.length === 0 ? (
        <p className="text-slate">У цьому місяці немає працівників у вашій області доступу.</p>
      ) : (
        <div className="overflow-x-auto">
          <table
            className="w-full min-w-[44rem] border-collapse text-left"
            aria-busy={report.isFetching}
          >
            <caption className="sr-only">Табель за місяць по працівниках, у робочих днях</caption>
            <thead className="text-sm text-slate">
              <tr>
                <th className="pb-3 font-normal">Працівник</th>
                {COLUMNS.map(([key, label]) => (
                  <th key={key} className="pb-3 text-right font-normal">
                    {label}
                  </th>
                ))}
                <th className="pb-3 text-right font-normal">Години</th>
              </tr>
            </thead>
            <tbody>
              {report.data.rows.map((row) => (
                <tr key={row.employee.id} className="border-t border-border">
                  <td className="py-3 pr-6">
                    <span className="block font-medium">{row.employee.name}</span>
                    <span className="block text-sm text-slate">{row.unit}</span>
                  </td>
                  {COLUMNS.map(([key]) => (
                    <td
                      key={key}
                      className={
                        key === "missing" && row.missing > 0
                          ? "py-3 text-right font-medium text-warning tabular-nums"
                          : "py-3 text-right tabular-nums"
                      }
                    >
                      {row[key] || <span className="text-slate">—</span>}
                    </td>
                  ))}
                  <td className="py-3 text-right tabular-nums">
                    {row.hours ? formatHours(row.hours) : <span className="text-slate">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
