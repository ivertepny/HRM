"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateUser } from "@/lib/admin-queries";
import { ApiError } from "@/lib/api/client";

/** Новий обліковий запис: людина отримує запрошення і сама задає пароль;
 *  роль Employee видається автоматично на бекенді. */
export function CreateUserForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const create = useCreateUser();
  const [values, setValues] = useState({ email: "", first_name: "", last_name: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    create.mutate(values, {
      onSuccess: (user) => {
        if (user.invite_sent) {
          toast.success(`Запрошення надіслано на ${user.email}`);
        } else {
          toast.warning("Обліковий запис створено, але лист не надіслано — спробуйте ще раз");
        }
        router.push(`/admin/users/${user.id}`);
      },
      onError: (error) => {
        if (error instanceof ApiError) setErrors(error.fieldErrors);
        toast.error(error.message);
      },
    });
  }

  const field = (
    key: keyof typeof values,
    label: string,
    props: React.ComponentProps<"input"> = {},
  ) => (
    <div className="grid gap-2">
      <Label htmlFor={`new-${key}`}>{label}</Label>
      <Input
        id={`new-${key}`}
        value={values[key]}
        onChange={set(key)}
        aria-invalid={!!errors[key]}
        className="h-10 bg-sheet"
        {...props}
      />
      {errors[key] && <p className="text-sm text-destructive">{errors[key]}</p>}
    </div>
  );

  return (
    <form onSubmit={submit} className="grid max-w-2xl gap-4 rounded-md bg-mist p-4">
      <p className="text-sm font-medium">Новий обліковий запис</p>
      <div className="grid gap-4 sm:grid-cols-2">
        {field("first_name", "Ім'я", { required: true, autoFocus: true })}
        {field("last_name", "Прізвище", { required: true })}
      </div>
      {field("email", "Робоча пошта", { type: "email", required: true, autoComplete: "off" })}
      <p className="text-xs text-slate">
        На цю пошту прийде запрошення: людина сама задасть пароль за посиланням (діє 7 днів).
        Новий запис отримує базову роль «Employee».
      </p>
      <span className="flex gap-2">
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Створюємо…" : "Створити і надіслати запрошення"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}
