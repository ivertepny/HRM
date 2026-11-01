"use client";

import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { unitPath, type Unit } from "@/lib/employees";
import { useCreateUnit, useUpdateUnit } from "@/lib/queries";

type Props = {
  /** Редагування — підрозділ; створення — undefined. */
  unit?: Unit;
  /** Для створення: батько нового підрозділу (undefined — верхній рівень). */
  parentId?: number;
  /** Можливі батьки (без самого підрозділу та його нащадків). */
  parents: Unit[];
  /** Наявні типи — підказки для поля «Тип». */
  types: string[];
  onDone: (unit: Unit) => void;
  onCancel: () => void;
};

export function UnitForm({ unit, parentId, parents, types, onDone, onCancel }: Props) {
  const create = useCreateUnit();
  const update = useUpdateUnit(unit?.id ?? 0);
  const [name, setName] = useState(unit?.name ?? "");
  const [type, setType] = useState(unit?.custom_type ?? "");
  const [parent, setParent] = useState(String((unit ? unit.parent : parentId) ?? ""));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const pending = create.isPending || update.isPending;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    if (!name.trim()) {
      setErrors({ name: "Вкажіть назву" });
      return;
    }
    const body = {
      name: name.trim(),
      custom_type: type.trim(),
      parent: parent ? Number(parent) : null,
    };
    const options = {
      onSuccess: (saved: Unit) => {
        toast.success(unit ? "Зміни збережено" : "Підрозділ створено");
        onDone(saved);
      },
      onError: (error: Error) => {
        if (error instanceof ApiError) setErrors(error.fieldErrors);
        toast.error(error.message);
      },
    };
    if (unit) update.mutate(body, options);
    else create.mutate(body, options);
  }

  return (
    <form onSubmit={submit} className="grid max-w-xl gap-4 rounded-md bg-mist p-4">
      <p className="text-sm font-medium">{unit ? "Редагування підрозділу" : "Новий підрозділ"}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="unit-name">Назва</Label>
          <Input
            id="unit-name"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={!!errors.name}
            className="h-10 bg-sheet"
          />
          {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="unit-type">Тип</Label>
          <Input
            id="unit-type"
            list="unit-types"
            placeholder="Департамент, відділ, команда…"
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="h-10 bg-sheet"
          />
          <datalist id="unit-types">
            {types.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="unit-parent">Входить до</Label>
        <NativeSelect
          id="unit-parent"
          value={parent}
          onChange={(e) => setParent(e.target.value)}
          className="bg-sheet"
        >
          <option value="">Верхній рівень компанії</option>
          {parents.map((p) => (
            <option key={p.id} value={p.id}>
              {unitPath(p)}
            </option>
          ))}
        </NativeSelect>
        {errors.parent && <p className="text-sm text-destructive">{errors.parent}</p>}
      </div>
      <span className="flex gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Зберігаємо…" : unit ? "Зберегти зміни" : "Створити підрозділ"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}
