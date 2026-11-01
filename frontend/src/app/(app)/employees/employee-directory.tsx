"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { NativeSelect } from "@/components/app/native-select";
import { PageHeader } from "@/components/app/section";
import { fullName, initials } from "@/components/app/user-name";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { useDebounced } from "@/lib/hooks";
import { fileHref, unitPath } from "@/lib/employees";
import { formatDate, LEVEL_LABELS, PEOPLE, plural } from "@/lib/format";
import { useEmployees, useMyAccess, useUnits } from "@/lib/queries";

const PAGE_SIZE = 20;

type Level = "trainee" | "junior" | "middle" | "senior";

export function EmployeeDirectory() {
  const access = useMyAccess();
  const units = useUnits(canAnywhere(access.data, "company:read"));
  const [search, setSearch] = useState("");
  // ?unit= — перехід з оргструктури («Переглянути працівників»)
  const params = useSearchParams();
  const [unit, setUnit] = useState(params.get("unit") ?? "");
  const [level, setLevel] = useState<Level | "">("");
  const [showFired, setShowFired] = useState(false);
  const [page, setPage] = useState(1);
  const term = useDebounced(search.trim());

  const employees = useEmployees({
    page,
    page_size: PAGE_SIZE,
    search: term || undefined,
    unit: unit ? Number(unit) : undefined,
    level: level || undefined,
    active: showFired ? undefined : true,
  });

  /** Новий фільтр — з першої сторінки. */
  const reset =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value);
      setPage(1);
    };

  const count = employees.data?.count ?? 0;
  const from = (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, count);

  return (
    <div className="grid gap-8">
      <PageHeader title="Працівники">
        {employees.isSuccess &&
          (count ? `${count} ${plural(count, PEOPLE)} у вашій області доступу.` : null)}
      </PageHeader>

      <div className="grid gap-4 border-t border-border pt-6 md:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)] md:items-end">
        <div className="grid gap-2">
          <Label htmlFor="search">Пошук</Label>
          <Input
            id="search"
            type="search"
            placeholder="Ім'я, пошта або посада"
            value={search}
            onChange={(e) => reset(setSearch)(e.target.value)}
            className="h-10"
          />
        </div>
        {units.data && (
          <div className="grid gap-2">
            <Label htmlFor="unit">Підрозділ</Label>
            <NativeSelect id="unit" value={unit} onChange={(e) => reset(setUnit)(e.target.value)}>
              <option value="">Усі підрозділи</option>
              {units.data.map((u) => (
                <option key={u.id} value={u.id}>
                  {unitPath(u)}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
        <div className="grid gap-2">
          <Label htmlFor="level">Рівень</Label>
          <NativeSelect id="level" value={level} onChange={(e) => reset(setLevel)(e.target.value as Level | "")}>
            <option value="">Будь-який</option>
            {Object.entries(LEVEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
        <label className="flex items-center gap-2 text-sm md:col-span-3">
          <input
            type="checkbox"
            checked={showFired}
            onChange={(e) => reset(setShowFired)(e.target.checked)}
            className="size-4 accent-primary"
          />
          Показувати звільнених
        </label>
      </div>

      {employees.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : employees.isError ? (
        <p role="alert">Не вдалося завантажити працівників: {employees.error.message}</p>
      ) : count === 0 ? (
        <p className="text-slate">
          {term || unit || level
            ? "Нікого не знайдено. Спробуйте інший запит або приберіть фільтри."
            : "Працівників ще немає."}
        </p>
      ) : (
        <>
          <table
            className="w-full border-collapse text-left"
            aria-busy={employees.isFetching}
          >
            <caption className="sr-only">Список працівників</caption>
            <thead className="text-sm text-slate">
              <tr className="hidden md:table-row">
                <th className="pb-3 font-normal">Працівник</th>
                <th className="pb-3 font-normal">Посада</th>
                <th className="pb-3 font-normal">Підрозділ</th>
                <th className="pb-3 font-normal">Рівень</th>
              </tr>
            </thead>
            <tbody>
              {employees.data.results.map((employee) => (
                <tr
                  key={employee.id}
                  className="grid gap-1 border-t border-border py-4 md:table-row md:py-0"
                >
                  <td className="md:py-3 md:pr-6">
                    <Link
                      href={`/employees/${employee.id}`}
                      className="group flex items-center gap-3 rounded-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                    >
                      <Avatar className="size-9">
                        {employee.photo && <AvatarImage src={fileHref(employee.photo)} alt="" />}
                        <AvatarFallback className="bg-mist text-sm text-ink">
                          {initials(employee.user)}
                        </AvatarFallback>
                      </Avatar>
                      <span>
                        <span className="block font-medium group-hover:underline">
                          {fullName(employee.user)}
                        </span>
                        <span className="block text-sm text-slate">{employee.user?.email}</span>
                      </span>
                    </Link>
                  </td>
                  <td className="md:py-3 md:pr-6">
                    {employee.position?.name}
                    {employee.date_fired && (
                      <span className="block text-sm text-slate">
                        звільнення {formatDate(employee.date_fired)}
                      </span>
                    )}
                  </td>
                  <td className="text-slate md:py-3 md:pr-6">{employee.structural_unit?.full_name}</td>
                  <td className="md:py-3">{employee.level ? LEVEL_LABELS[employee.level] : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <nav aria-label="Сторінки" className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-slate">
              {from}–{to} з {count}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Попередня
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!employees.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Наступна
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
