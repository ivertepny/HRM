"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { useSubmitVacation } from "@/lib/queries";
import {
  calendarDays,
  daysInclusive,
  PLANNED_TYPES,
  todayISO,
  TYPE_LABELS,
  type VacationType,
} from "@/lib/vacations";

const schema = z
  .object({
    vacation_type: z.enum(["annual", "sick", "unpaid", "other"]),
    date_start: z.string().min(1, "Вкажіть першу дату"),
    date_end: z.string().min(1, "Вкажіть останню дату"),
    comment: z.string().max(500, "До 500 символів"),
  })
  .refine((v) => !v.date_start || !v.date_end || v.date_end >= v.date_start, {
    path: ["date_end"],
    message: "Остання дата не може бути раніше першої",
  })
  .refine((v) => !PLANNED_TYPES.includes(v.vacation_type) || v.date_start >= todayISO(), {
    path: ["date_start"],
    message: "Цей тип відпустки не можна почати в минулому",
  });

type Values = z.infer<typeof schema>;

export function VacationForm() {
  const submit = useSubmitVacation();
  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { vacation_type: "annual", date_start: "", date_end: "", comment: "" },
  });
  const [start, end] = useWatch({ control, name: ["date_start", "date_end"] });
  const days = start && end ? daysInclusive(start, end) : 0;

  function onSubmit(values: Values) {
    submit.mutate(values, {
      onSuccess: () => {
        reset();
        toast.success("Заявку подано — HR отримає її на розгляд");
      },
      onError: (error) => {
        const fields = error instanceof ApiError ? error.fieldErrors : {};
        for (const [field, message] of Object.entries(fields)) {
          if (field in values) setError(field as keyof Values, { message });
        }
        // Помилка без поля (перетин дат, 503) лишається видимою біля кнопки
        if (!Object.keys(fields).some((field) => field in values)) {
          setError("root", { message: error.message });
        }
      },
    });
  }

  const fieldError = (name: keyof Values) =>
    errors[name] && (
      <p id={`${name}-error`} className="text-sm text-destructive">
        {errors[name]?.message}
      </p>
    );

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="grid gap-5">
      <div className="grid gap-2">
        <Label htmlFor="vacation_type">Тип</Label>
        <NativeSelect id="vacation_type" {...register("vacation_type")}>
          {(Object.keys(TYPE_LABELS) as VacationType[]).map((type) => (
            <option key={type} value={type}>
              {TYPE_LABELS[type]}
            </option>
          ))}
        </NativeSelect>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        {(
          [
            ["date_start", "Перший день"],
            ["date_end", "Останній день"],
          ] as const
        ).map(([name, label]) => (
          <div key={name} className="grid gap-2">
            <Label htmlFor={name}>{label}</Label>
            <Input
              id={name}
              type="date"
              className="h-10"
              aria-invalid={!!errors[name]}
              aria-describedby={errors[name] ? `${name}-error` : undefined}
              {...register(name)}
            />
            {fieldError(name)}
          </div>
        ))}
      </div>
      <p className="-mt-2 text-sm text-slate" aria-live="polite">
        {days > 0 ? calendarDays(days) : "Оберіть дати — кількість днів порахуємо самі."}
      </p>

      <div className="grid gap-2">
        <Label htmlFor="comment">Коментар для HR (необов&apos;язково)</Label>
        <Textarea id="comment" rows={2} {...register("comment")} />
        {fieldError("comment")}
      </div>

      {errors.root && (
        <p role="alert" className="text-sm text-destructive">
          {errors.root.message}
        </p>
      )}

      <div>
        <Button type="submit" disabled={submit.isPending}>
          {submit.isPending ? "Подаємо…" : "Подати заявку"}
        </Button>
      </div>
    </form>
  );
}
