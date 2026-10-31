"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useVacations } from "@/lib/queries";
import {
  calendarRows,
  formatRange,
  monthDays,
  STATUS_LABELS,
  toISODate,
  TYPE_LABELS,
  type CalendarSegment,
} from "@/lib/vacations";

const monthTitle = new Intl.DateTimeFormat("uk-UA", { month: "long", year: "numeric" });
const weekday = new Intl.DateTimeFormat("uk-UA", { weekday: "short" });

function title(year: number, month: number) {
  const text = monthTitle.format(new Date(year, month, 1)).replace(" р.", "");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function describe(name: string, segment: CalendarSegment) {
  const { vacation } = segment;
  return `${name}: ${formatRange(vacation.date_start, vacation.date_end)}, ${
    TYPE_LABELS[vacation.vacation_type ?? "annual"]
  }, ${STATUS_LABELS[vacation.status!].toLowerCase()}`;
}

/** Хто й коли відсутній: працівники × дні місяця. */
export function TeamCalendar() {
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const { year, month } = cursor;
  const days = monthDays(year, month);

  const vacations = useVacations({
    date_from: toISODate(new Date(year, month, 1)),
    date_to: toISODate(new Date(year, month + 1, 0)),
  });
  const rows = calendarRows(vacations.data ?? [], year, month);

  const shift = (delta: number) =>
    setCursor(({ year, month }) => {
      const date = new Date(year, month + delta, 1);
      return { year: date.getFullYear(), month: date.getMonth() };
    });

  const columns = { gridTemplateColumns: `11rem repeat(${days.length}, minmax(1.6rem, 1fr))` };

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="font-heading min-w-48 text-[1.375rem] font-medium" aria-live="polite">
          {title(year, month)}
        </h3>
        <span className="inline-flex gap-1">
          <Button variant="outline" size="sm" aria-label="Попередній місяць" onClick={() => shift(-1)}>
            ‹
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCursor({ year: now.getFullYear(), month: now.getMonth() })}
          >
            Цей місяць
          </Button>
          <Button variant="outline" size="sm" aria-label="Наступний місяць" onClick={() => shift(1)}>
            ›
          </Button>
        </span>
      </div>

      {vacations.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : vacations.isError ? (
        <p role="alert">Не вдалося завантажити календар: {vacations.error.message}</p>
      ) : rows.length === 0 ? (
        <p className="text-slate">Цього місяця ніхто з команди не у відпустці.</p>
      ) : (
        <>
          {/* Для скрінрідерів — той самий зміст списком */}
          <ul className="sr-only">
            {rows.flatMap((row) =>
              row.segments.map((segment) => (
                <li key={segment.vacation.id}>{describe(row.name, segment)}</li>
              )),
            )}
          </ul>

          <div aria-hidden className="overflow-x-auto pb-2">
            <div className="min-w-[56rem] text-sm">
              <div className="grid" style={columns}>
                <span className="sticky left-0 z-10 bg-sheet" />
                {days.map((d) => (
                  <span
                    key={d.iso}
                    className={cn(
                      "flex flex-col items-center py-1 tabular-nums",
                      d.weekend ? "text-slate/60" : "text-slate",
                      d.today && "rounded-t-sm bg-ink font-semibold text-mist",
                    )}
                  >
                    <span className="text-[0.6875rem]">
                      {weekday.format(new Date(year, month, d.day))}
                    </span>
                    {d.day}
                  </span>
                ))}
              </div>

              {rows.map((row) => (
                <div key={row.employeeId} className="grid border-t border-border" style={columns}>
                  {/* Ім'я лишається видимим при горизонтальному прокручуванні */}
                  <span className="sticky left-0 z-10 row-start-1 truncate bg-sheet py-2.5 pr-3 font-medium">
                    {row.name}
                  </span>
                  {days.map((d, i) => (
                    <span
                      key={d.iso}
                      className={cn(
                        "row-start-1",
                        d.weekend && "bg-mist",
                        d.today && "bg-ink/8",
                      )}
                      style={{ gridColumn: i + 2 }}
                    />
                  ))}
                  {row.segments.map((segment) => (
                    <span
                      key={segment.vacation.id}
                      title={describe(row.name, segment)}
                      className={cn(
                        "row-start-1 mx-px h-5 self-center rounded-sm",
                        segment.vacation.status === "approved" ? "bg-primary" : "vacation-pending",
                        segment.continuesBefore && "rounded-l-none",
                        segment.continuesAfter && "rounded-r-none",
                      )}
                      style={{ gridColumn: `${segment.column + 1} / span ${segment.span}` }}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>

          <p className="flex flex-wrap gap-5 text-sm text-slate">
            <span className="inline-flex items-center gap-2">
              <span className="h-3 w-6 rounded-sm bg-primary" /> Схвалено
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="vacation-pending h-3 w-6 rounded-sm" /> На розгляді
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="h-3 w-6 rounded-sm bg-mist ring-1 ring-border" /> Вихідні
            </span>
          </p>
        </>
      )}
    </div>
  );
}
