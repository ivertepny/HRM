"use client";

import { useState } from "react";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, type Schemas } from "@/lib/api/client";
import { CATEGORY_LABELS, type Equipment, type EquipmentCategory } from "@/lib/equipment";

type Values = Schemas["EquipmentRequest"];

/** Створення й редагування одиниці. onSubmit кидає ApiError — помилки біля полів. */
export function EquipmentForm({
  initial,
  submitLabel,
  pendingLabel,
  onSubmit,
  onCancel,
}: {
  initial?: Equipment;
  submitLabel: string;
  pendingLabel: string;
  onSubmit: (values: Values) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<Values>({
    name: initial?.name ?? "",
    category: initial?.category ?? "laptop",
    serial_number: initial?.serial_number ?? "",
    description: initial?.description ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const set = (field: keyof Values) => (value: string) =>
    setValues((current) => ({ ...current, [field]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setGeneral(null);
    try {
      await onSubmit({
        ...values,
        name: values.name.trim(),
        serial_number: values.serial_number.trim(),
      });
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
        setErrors(error.fieldErrors);
      } else {
        setGeneral(error instanceof Error ? error.message : String(error));
      }
    } finally {
      setPending(false);
    }
  }

  const fieldError = (field: string) =>
    errors[field] && (
      <p id={`${field}-error`} className="text-sm text-destructive">
        {errors[field]}
      </p>
    );

  return (
    <form onSubmit={submit} className="grid max-w-2xl gap-4 rounded-md bg-mist p-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="grid gap-2">
          <Label htmlFor="eq-name">Назва</Label>
          <Input
            id="eq-name"
            required
            maxLength={200}
            value={values.name}
            onChange={(e) => set("name")(e.target.value)}
            placeholder="Напр.: Lenovo ThinkPad T14"
            aria-invalid={Boolean(errors.name)}
            aria-describedby={errors.name ? "name-error" : undefined}
            className="h-10 bg-sheet"
          />
          {fieldError("name")}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="eq-category">Категорія</Label>
          <NativeSelect
            id="eq-category"
            value={values.category}
            onChange={(e) => set("category")(e.target.value as EquipmentCategory)}
            className="bg-sheet"
          >
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="eq-serial">Серійний номер</Label>
        <Input
          id="eq-serial"
          required
          maxLength={100}
          value={values.serial_number}
          onChange={(e) => set("serial_number")(e.target.value)}
          aria-invalid={Boolean(errors.serial_number)}
          aria-describedby={errors.serial_number ? "serial_number-error" : undefined}
          className="h-10 bg-sheet font-mono"
        />
        {fieldError("serial_number")}
      </div>
      <div className="grid gap-2">
        <Label htmlFor="eq-description">Опис</Label>
        <Textarea
          id="eq-description"
          rows={2}
          value={values.description}
          onChange={(e) => set("description")(e.target.value)}
          placeholder="Комплектація, стан, де зберігається"
          className="bg-sheet"
        />
      </div>
      {general && (
        <p role="alert" className="text-sm text-destructive">
          {general}
        </p>
      )}
      <span className="flex gap-2">
        <Button
          type="submit"
          disabled={pending || !values.name.trim() || !values.serial_number.trim()}
        >
          {pending ? pendingLabel : submitLabel}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}
