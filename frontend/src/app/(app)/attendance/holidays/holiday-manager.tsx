"use client";

import { useState } from "react";
import { toast } from "sonner";

import { PageHeader, Section } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { ApiError } from "@/lib/api/client";
import { dayLabel } from "@/lib/attendance";
import { useCreateHoliday, useDeleteHoliday, useHolidays, useMyAccess } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

/** Календар неробочих днів компанії. Свята, що припадають на пн–пт,
 *  не рахуються робочими днями в табелі. */
export function HolidayManager() {
  const access = useMyAccess();
  const canManage = canAnywhere(access.data, "attendance:manage");
  const [year, setYear] = useState(() => Number(todayISO().slice(0, 4)));
  const holidays = useHolidays({ year });
  const remove = useDeleteHoliday();

  return (
    <div className="grid gap-10">
      <PageHeader title="Святкові дні">
        Неробочі дні компанії: у табелі вони не рахуються робочими, а дні без відмітки в них не
        вважаються пропуском. Під час воєнного стану державні свята в Україні — робочі дні, тож
        календар веде HR, а не система.
      </PageHeader>

      <Section title={`${year} рік`} wide>
        <div className="grid gap-5">
          <div className="flex items-center gap-2" role="group" aria-label="Рік">
            <Button variant="outline" size="sm" onClick={() => setYear((y) => y - 1)}>
              ← {year - 1}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setYear((y) => y + 1)}>
              {year + 1} →
            </Button>
          </div>

          {canManage && <HolidayForm year={year} />}

          {holidays.isPending ? (
            <Skeleton className="h-32 w-full" />
          ) : holidays.isError ? (
            <p role="alert">Не вдалося завантажити свята: {holidays.error.message}</p>
          ) : holidays.data.length === 0 ? (
            <p className="text-slate">У {year} році святкових днів не задано.</p>
          ) : (
            <ul className="grid">
              {holidays.data.map((holiday) => (
                <li
                  key={holiday.id}
                  className="flex items-center justify-between gap-4 border-t border-border py-3"
                >
                  <span>
                    <span className="block font-medium">{holiday.name}</span>
                    <span className="block text-sm text-slate">{dayLabel(holiday.date)}</span>
                  </span>
                  {canManage && (
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={remove.isPending}
                      aria-label={`Видалити «${holiday.name}»`}
                      onClick={() =>
                        remove.mutate(holiday.id!, {
                          onSuccess: () => toast.success("Свято видалено"),
                          onError: (error) => toast.error(error.message),
                        })
                      }
                    >
                      Видалити
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Section>
    </div>
  );
}

function HolidayForm({ year }: { year: number }) {
  const create = useCreateHoliday();
  const [errors, setErrors] = useState<Record<string, string>>({});

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const body = { date: String(form.get("date") ?? ""), name: String(form.get("name") ?? "") };
    setErrors({});
    create.mutate(body, {
      onSuccess: () => {
        toast.success("Свято додано");
        formElement.reset();
      },
      onError: (error) => {
        if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
          setErrors(error.fieldErrors);
        } else {
          toast.error(error.message);
        }
      },
    });
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      className="grid gap-4 rounded-md bg-mist p-4 sm:grid-cols-[12rem_1fr_auto] sm:items-end"
    >
      <div className="grid gap-2">
        <Label htmlFor="holiday-date">Дата</Label>
        <Input
          id="holiday-date"
          name="date"
          type="date"
          min={`${year}-01-01`}
          max={`${year}-12-31`}
          required
          aria-invalid={!!errors.date}
          aria-describedby={errors.date ? "holiday-date-error" : undefined}
          className="h-10 bg-sheet"
        />
        {errors.date && (
          <p id="holiday-date-error" className="text-sm text-destructive">
            {errors.date}
          </p>
        )}
      </div>
      <div className="grid gap-2">
        <Label htmlFor="holiday-name">Назва</Label>
        <Input
          id="holiday-name"
          name="name"
          required
          maxLength={200}
          placeholder="Напр.: Різдво, корпоративний вихідний"
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? "holiday-name-error" : undefined}
          className="h-10 bg-sheet"
        />
        {errors.name && (
          <p id="holiday-name-error" className="text-sm text-destructive">
            {errors.name}
          </p>
        )}
      </div>
      <Button type="submit" disabled={create.isPending} className="h-10">
        {create.isPending ? "Додаємо…" : "Додати свято"}
      </Button>
    </form>
  );
}
