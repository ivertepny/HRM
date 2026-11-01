"use client";

import { useState } from "react";

import { MonthSwitcher } from "@/components/app/month-switcher";
import { PageHeader, Section } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  dayLabel,
  formatHours,
  monthOf,
  monthRange,
  shortTime,
  STATUS_LABELS,
} from "@/lib/attendance";
import { useAttendance, useMe, useMyEmployee } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

import { DayForm } from "./day-form";

export function MyTimesheet() {
  const me = useMe();
  const employee = useMyEmployee(me.data?.id);
  const today = todayISO();
  const [month, setMonth] = useState(monthOf(today));
  const [editing, setEditing] = useState<number | "other" | null>(null);
  const employeeId = employee.data?.id;

  const todayRecord = useAttendance(
    { employee: employeeId, date_from: today, date_to: today },
    employeeId !== undefined,
  );
  const { from, to } = monthRange(month);
  const records = useAttendance(
    { employee: employeeId, date_from: from, date_to: to },
    employeeId !== undefined,
  );

  if (me.isPending || employee.isPending) {
    return <Skeleton className="h-64 w-full max-w-2xl" />;
  }
  if (!employee.data) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Мій табель" />
        <p className="text-slate">
          У вас немає профілю працівника — табель ведуть лише працівники.
        </p>
      </div>
    );
  }

  const current = todayRecord.data?.[0];

  return (
    <div className="grid gap-10">
      <PageHeader title="Мій табель">
        Відмічайте, де працюєте. Виправити можна відмітки за останній тиждень.
      </PageHeader>

      <Section title={current ? "Сьогодні — відмічено" : "Сьогодні"}>
        {todayRecord.isPending ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          // key: після відмітки форма перемикається на виправлення
          <DayForm key={current?.id ?? "new"} record={current} />
        )}
      </Section>

      <Section title="Місяць" wide>
        <div className="grid gap-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <MonthSwitcher
              month={month}
              max={monthOf(today)}
              onChange={(value) => {
                setMonth(value);
                setEditing(null);
              }}
            />
            {editing === null && (
              <Button variant="outline" onClick={() => setEditing("other")}>
                Відмітити інший день
              </Button>
            )}
          </div>

          {editing === "other" && (
            <div className="rounded-md bg-mist p-4">
              <DayForm pickDate onDone={() => setEditing(null)} />
            </div>
          )}

          {records.isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : records.isError ? (
            <p role="alert">Не вдалося завантажити табель: {records.error.message}</p>
          ) : records.data.length === 0 ? (
            <p className="text-slate">За цей місяць відміток немає.</p>
          ) : (
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Відмітки за місяць</caption>
              <thead className="text-sm text-slate">
                <tr className="hidden md:table-row">
                  <th className="pb-3 font-normal">День</th>
                  <th className="pb-3 font-normal">Де</th>
                  <th className="pb-3 font-normal">Час</th>
                  <th className="pb-3 font-normal">
                    <span className="sr-only">Дії</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {records.data.map((record) =>
                  editing === record.id ? (
                    <tr key={record.id} className="block md:table-row">
                      <td colSpan={4} className="block border-t border-border py-4 md:table-cell">
                        <p className="mb-3 font-medium">{dayLabel(record.date!)}</p>
                        <DayForm record={record} onDone={() => setEditing(null)} />
                      </td>
                    </tr>
                  ) : (
                    <tr
                      key={record.id}
                      className="grid gap-1 border-t border-border py-4 md:table-row md:py-0"
                    >
                      <td className="font-medium md:py-3 md:pr-6">{dayLabel(record.date!)}</td>
                      <td className="md:py-3 md:pr-6">
                        {STATUS_LABELS[record.status]}
                        {record.comment && (
                          <span className="block text-sm text-slate">«{record.comment}»</span>
                        )}
                      </td>
                      <td className="tabular-nums md:py-3 md:pr-6">
                        {record.time_start ? (
                          <>
                            {shortTime(record.time_start)}–{shortTime(record.time_end) ?? "…"}
                            {record.hours != null && (
                              <span className="block text-sm text-slate">
                                {formatHours(record.hours)}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-slate">—</span>
                        )}
                      </td>
                      <td className="md:py-3 md:text-right">
                        {record.editable && (
                          <Button size="sm" variant="ghost" onClick={() => setEditing(record.id!)}>
                            Виправити
                          </Button>
                        )}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          )}
        </div>
      </Section>
    </div>
  );
}
