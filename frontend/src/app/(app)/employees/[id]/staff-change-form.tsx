"use client";

import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { changedFields, CURRENCIES, unitPath, type Employee } from "@/lib/employees";
import { LEVEL_LABELS } from "@/lib/format";
import { usePositions, useUnits, useUpdateEmployee } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

type Draft = {
  position_id: string;
  structural_unit_id: string;
  level: string;
  salary: string;
  salary_currency: string;
};

function draftOf(employee: Employee): Draft {
  return {
    position_id: String(employee.position?.id ?? ""),
    structural_unit_id: String(employee.structural_unit?.id ?? ""),
    level: employee.level ?? "",
    salary: employee.salary ?? "",
    salary_currency: employee.salary_currency ?? "UAH",
  };
}

/**
 * Переведення, підвищення, зміна зарплати. Кожне збереження — запис у
 * кадровому журналі з причиною й датою, тому надсилаємо лише змінене.
 */
export function StaffChangeForm({
  employee,
  canEditSalary,
  canChangeUnit,
}: {
  employee: Employee;
  canEditSalary: boolean;
  canChangeUnit: boolean;
}) {
  const positions = usePositions();
  const units = useUnits(canChangeUnit);
  const update = useUpdateEmployee(employee.id!);
  const initial = draftOf(employee);
  const [draft, setDraft] = useState(initial);
  const [effectiveDate, setEffectiveDate] = useState(todayISO());
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const changes = changedFields(initial, draft);
  const hasChanges = Object.keys(changes).length > 0;
  const set = (key: keyof Draft) => (value: string) => setDraft((d) => ({ ...d, [key]: value }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    update.mutate(
      {
        ...(changes.position_id && { position_id: Number(changes.position_id) }),
        ...(changes.structural_unit_id && {
          structural_unit_id: Number(changes.structural_unit_id),
        }),
        ...("level" in changes && { level: changes.level as Employee["level"] }),
        ...("salary" in changes && { salary: changes.salary || null }),
        ...(changes.salary_currency && {
          salary_currency: changes.salary_currency as Employee["salary_currency"],
        }),
        change_reason: reason,
        effective_date: effectiveDate,
      },
      {
        onSuccess: (saved) => {
          setDraft(draftOf(saved));
          setReason("");
          toast.success("Зміну збережено й додано до кадрового журналу");
        },
        onError: (error) => {
          if (error instanceof ApiError) setErrors(error.fieldErrors);
          toast.error(error.message);
        },
      },
    );
  }

  const error = (field: string) =>
    errors[field] && <p className="text-sm text-destructive">{errors[field]}</p>;

  return (
    <form onSubmit={submit} className="grid gap-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="position">Посада</Label>
          <NativeSelect
            id="position"
            value={draft.position_id}
            onChange={(e) => set("position_id")(e.target.value)}
          >
            {(positions.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
            {!positions.data && <option value={draft.position_id}>{employee.position?.name}</option>}
          </NativeSelect>
          {error("position_id")}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="level">Рівень</Label>
          <NativeSelect id="level" value={draft.level} onChange={(e) => set("level")(e.target.value)}>
            <option value="">Не вказано</option>
            {Object.entries(LEVEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
          {error("level")}
        </div>
      </div>

      {canChangeUnit && (
        <div className="grid gap-2">
          <Label htmlFor="unit">Підрозділ</Label>
          <NativeSelect
            id="unit"
            value={draft.structural_unit_id}
            onChange={(e) => set("structural_unit_id")(e.target.value)}
          >
            {(units.data ?? []).map((u) => (
              <option key={u.id} value={u.id}>
                {unitPath(u)}
              </option>
            ))}
            {!units.data && (
              <option value={draft.structural_unit_id}>{employee.structural_unit?.full_name}</option>
            )}
          </NativeSelect>
          {error("structural_unit_id")}
        </div>
      )}

      {canEditSalary && (
        <div className="grid gap-5 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="grid gap-2">
            <Label htmlFor="salary">Зарплата</Label>
            <Input
              id="salary"
              inputMode="decimal"
              value={draft.salary}
              onChange={(e) => set("salary")(e.target.value)}
              className="h-10 tabular-nums"
            />
            {error("salary")}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="currency">Валюта</Label>
            <NativeSelect
              id="currency"
              value={draft.salary_currency}
              onChange={(e) => set("salary_currency")(e.target.value)}
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </NativeSelect>
          </div>
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="grid gap-2">
          <Label htmlFor="effective">Діє з</Label>
          <Input
            id="effective"
            type="date"
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.target.value)}
            className="h-10"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="reason">Причина — потрапить у кадровий журнал</Label>
          <Textarea
            id="reason"
            rows={1}
            maxLength={255}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Напр.: підвищення за результатами ревʼю"
          />
        </div>
      </div>

      <div>
        <Button type="submit" disabled={!hasChanges || update.isPending}>
          {update.isPending ? "Зберігаємо…" : "Зберегти зміну"}
        </Button>
      </div>
    </form>
  );
}
