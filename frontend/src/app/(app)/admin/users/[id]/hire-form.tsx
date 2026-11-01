"use client";

import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useHire } from "@/lib/admin-queries";
import { ApiError, type Schemas } from "@/lib/api/client";
import { CURRENCIES, unitPath } from "@/lib/employees";
import { LEVEL_LABELS } from "@/lib/format";
import { usePositions, useUnits } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

/** Прийом на роботу: профіль працівника для облікового запису + запис «Прийом» у журналі. */
export function HireForm({ userId, canSetSalary }: { userId: number; canSetSalary: boolean }) {
  const positions = usePositions();
  const units = useUnits();
  const hire = useHire();
  const [values, setValues] = useState({
    position_id: "",
    structural_unit_id: "",
    level: "",
    salary: "",
    salary_currency: "UAH",
    date_hired: todayISO(),
    change_reason: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (key: keyof typeof values) => (value: string) =>
    setValues((v) => ({ ...v, [key]: value }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    const missing: Record<string, string> = {};
    if (!values.position_id) missing.position_id = "Оберіть посаду";
    if (!values.structural_unit_id) missing.structural_unit_id = "Оберіть підрозділ";
    if (Object.keys(missing).length) {
      setErrors(missing);
      return;
    }
    hire.mutate(
      {
        user_id: userId,
        position_id: Number(values.position_id),
        structural_unit_id: Number(values.structural_unit_id),
        level: values.level as Schemas["EmployeeRequest"]["level"],
        date_hired: values.date_hired,
        change_reason: values.change_reason,
        ...(canSetSalary && values.salary
          ? {
              salary: values.salary,
              salary_currency: values.salary_currency as Schemas["EmployeeRequest"]["salary_currency"],
            }
          : {}),
      },
      {
        onSuccess: () => toast.success("Прийом оформлено"),
        onError: (error) => {
          if (error instanceof ApiError) setErrors(error.fieldErrors);
          toast.error(error.message);
        },
      },
    );
  }

  const error = (key: string) =>
    errors[key] && <p className="text-sm text-destructive">{errors[key]}</p>;

  return (
    <form onSubmit={submit} className="grid max-w-xl gap-4 rounded-md bg-mist p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="hire-position">Посада</Label>
          <NativeSelect
            id="hire-position"
            value={values.position_id}
            onChange={(e) => set("position_id")(e.target.value)}
            className="bg-sheet"
          >
            <option value="">Оберіть посаду</option>
            {(positions.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </NativeSelect>
          {error("position_id")}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="hire-level">Рівень</Label>
          <NativeSelect
            id="hire-level"
            value={values.level}
            onChange={(e) => set("level")(e.target.value)}
            className="bg-sheet"
          >
            <option value="">Не вказано</option>
            {Object.entries(LEVEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="hire-unit">Підрозділ</Label>
        <NativeSelect
          id="hire-unit"
          value={values.structural_unit_id}
          onChange={(e) => set("structural_unit_id")(e.target.value)}
          className="bg-sheet"
        >
          <option value="">Оберіть підрозділ</option>
          {(units.data ?? []).map((u) => (
            <option key={u.id} value={u.id}>
              {unitPath(u)}
            </option>
          ))}
        </NativeSelect>
        {error("structural_unit_id")}
      </div>
      {canSetSalary && (
        <div className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="grid gap-2">
            <Label htmlFor="hire-salary">Зарплата</Label>
            <Input
              id="hire-salary"
              inputMode="decimal"
              value={values.salary}
              onChange={(e) => set("salary")(e.target.value)}
              className="h-10 bg-sheet tabular-nums"
            />
            {error("salary")}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="hire-currency">Валюта</Label>
            <NativeSelect
              id="hire-currency"
              value={values.salary_currency}
              onChange={(e) => set("salary_currency")(e.target.value)}
              className="bg-sheet"
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </NativeSelect>
          </div>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="grid gap-2">
          <Label htmlFor="hire-date">Перший робочий день</Label>
          <Input
            id="hire-date"
            type="date"
            value={values.date_hired}
            onChange={(e) => set("date_hired")(e.target.value)}
            className="h-10 bg-sheet"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="hire-reason">Підстава</Label>
          <Input
            id="hire-reason"
            maxLength={255}
            placeholder="Напр.: наказ № 15-к"
            value={values.change_reason}
            onChange={(e) => set("change_reason")(e.target.value)}
            className="h-10 bg-sheet"
          />
        </div>
      </div>
      {error("user_id")}
      <div>
        <Button type="submit" disabled={hire.isPending}>
          {hire.isPending ? "Оформлюємо…" : "Оформити прийом"}
        </Button>
      </div>
    </form>
  );
}
