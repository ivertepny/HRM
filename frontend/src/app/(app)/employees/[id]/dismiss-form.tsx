"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Employee } from "@/lib/employees";
import { useUpdateEmployee } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

/** Звільнення — окремо від кадрових змін: це незворотна для працівника подія. */
export function DismissForm({ employee }: { employee: Employee }) {
  const update = useUpdateEmployee(employee.id!);
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(todayISO());
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        Оформити звільнення
      </Button>
    );
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    update.mutate(
      { date_fired: date, change_reason: reason },
      {
        onSuccess: () => toast.success("Звільнення оформлено"),
        onError: (error) => toast.error(error.message),
      },
    );
  }

  return (
    <form onSubmit={submit} className="grid max-w-xl gap-4 rounded-md bg-mist p-4">
      <p className="text-sm">
        Працівник зберігає доступ до системи до дати звільнення. Скасувати звільнення
        потім можна лише окремою кадровою зміною.
      </p>
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="grid gap-2">
          <Label htmlFor="date_fired">Останній робочий день</Label>
          <Input
            id="date_fired"
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-10 bg-sheet"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="fire_reason">Підстава</Label>
          <Input
            id="fire_reason"
            maxLength={255}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Напр.: за власним бажанням"
            className="h-10 bg-sheet"
          />
        </div>
      </div>
      <span className="flex gap-2">
        <Button type="submit" variant="destructive" disabled={update.isPending}>
          {update.isPending ? "Оформлюємо…" : "Підтвердити звільнення"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
          Не звільняти
        </Button>
      </span>
    </form>
  );
}
