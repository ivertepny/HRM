"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import {
  nowTime,
  shortTime,
  STATUS_LABELS,
  type AttendanceRecord,
  type AttendanceStatus,
} from "@/lib/attendance";
import { useDeleteAttendance, useMarkAttendance, useUpdateAttendance } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

/** Відмітка за день: нова (record відсутній) або виправлення наявної.
 *  pickDate — дату можна обрати (відмітка за інший день). */
export function DayForm({
  record,
  date: initialDate = todayISO(),
  pickDate = false,
  onDone,
}: {
  record?: AttendanceRecord;
  date?: string;
  pickDate?: boolean;
  onDone?: () => void;
}) {
  const mark = useMarkAttendance();
  const update = useUpdateAttendance();
  const remove = useDeleteAttendance();

  const [date, setDate] = useState(record?.date ?? initialDate);
  const [status, setStatus] = useState<AttendanceStatus>(record?.status ?? "office");
  const [start, setStart] = useState(shortTime(record?.time_start) ?? "");
  const [end, setEnd] = useState(shortTime(record?.time_end) ?? "");
  const [comment, setComment] = useState(record?.comment ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);

  const working = status !== "off";
  const isToday = date === todayISO();
  const pending = mark.isPending || update.isPending || remove.isPending;

  function onError(error: Error) {
    if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
      setErrors(error.fieldErrors);
    } else {
      setGeneral(error.message);
    }
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    setGeneral(null);
    const body = {
      status,
      time_start: working && start ? start : null,
      time_end: working && end ? end : null,
      comment,
    };
    const onSuccess = () => {
      toast.success("Збережено");
      onDone?.();
    };
    if (record) {
      update.mutate({ id: record.id!, body }, { onSuccess, onError });
    } else {
      mark.mutate({ ...body, date }, { onSuccess, onError });
    }
  }

  const fieldError = (field: string) =>
    errors[field] && (
      <p id={`${field}-error`} className="text-sm text-destructive">
        {errors[field]}
      </p>
    );

  return (
    <form onSubmit={submit} className="grid max-w-2xl gap-5" noValidate>
      {pickDate && !record && (
        <div className="grid max-w-56 gap-2">
          <Label htmlFor="att-date">День</Label>
          <Input
            id="att-date"
            type="date"
            required
            max={todayISO()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            aria-invalid={Boolean(errors.date)}
            aria-describedby={errors.date ? "date-error" : undefined}
            className="h-10"
          />
          {fieldError("date")}
        </div>
      )}

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-sm font-medium">Де працюю</legend>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(STATUS_LABELS) as AttendanceStatus[]).map((value) => (
            <label
              key={value}
              className="flex cursor-pointer items-center gap-2 rounded-md border border-input px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50"
            >
              <input
                type="radio"
                name="att-status"
                value={value}
                checked={status === value}
                onChange={() => setStatus(value)}
                className="size-4 accent-primary"
              />
              {STATUS_LABELS[value]}
            </label>
          ))}
        </div>
      </fieldset>

      {working && (
        <div className="grid gap-4 sm:grid-cols-2">
          <TimeField
            id="att-start"
            label="Початок"
            value={start}
            onChange={setStart}
            error={fieldError("time_start")}
            invalid={Boolean(errors.time_start)}
            errorId="time_start-error"
            showNow={isToday && !start}
          />
          <TimeField
            id="att-end"
            label="Кінець"
            value={end}
            onChange={setEnd}
            error={fieldError("time_end")}
            invalid={Boolean(errors.time_end)}
            errorId="time_end-error"
            showNow={isToday && Boolean(start) && !end}
          />
        </div>
      )}

      <div className="grid gap-2">
        <Label htmlFor="att-comment">Коментар</Label>
        <Input
          id="att-comment"
          maxLength={500}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Напр.: відрядження, лікар до обіду"
          className="h-10"
        />
      </div>

      {general && (
        <p role="alert" className="text-sm text-destructive">
          {general}
        </p>
      )}
      {!pickDate && errors.date && (
        <p role="alert" className="text-sm text-destructive">
          {errors.date}
        </p>
      )}

      <span className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Зберігаємо…" : record ? "Зберегти зміни" : "Відмітитись"}
        </Button>
        {record && (
          <Button
            type="button"
            variant="ghost"
            disabled={pending}
            onClick={() =>
              remove.mutate(record.id!, {
                onSuccess: () => {
                  toast.success("Відмітку видалено");
                  onDone?.();
                },
                onError,
              })
            }
          >
            Видалити відмітку
          </Button>
        )}
        {onDone && (
          <Button type="button" variant="ghost" onClick={onDone}>
            Скасувати
          </Button>
        )}
      </span>
    </form>
  );
}

function TimeField({
  id,
  label,
  value,
  onChange,
  error,
  invalid,
  showNow,
  errorId,
}: {
  id: string;
  errorId: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  error: React.ReactNode;
  invalid: boolean;
  showNow: boolean;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <span className="flex gap-2">
        <Input
          id={id}
          type="time"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={invalid}
          aria-describedby={invalid ? errorId : undefined}
          className="h-10"
        />
        {showNow && (
          <Button
            type="button"
            variant="outline"
            className="h-10"
            onClick={() => onChange(nowTime())}
          >
            Зараз
          </Button>
        )}
      </span>
      {error}
    </div>
  );
}
