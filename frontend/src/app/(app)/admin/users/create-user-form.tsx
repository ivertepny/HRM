"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateUser } from "@/lib/admin-queries";
import { generatePassword } from "@/lib/admin";
import { ApiError } from "@/lib/api/client";

/** Новий обліковий запис: роль Employee видається автоматично на бекенді. */
export function CreateUserForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const create = useCreateUser();
  const [values, setValues] = useState({ email: "", first_name: "", last_name: "", password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    create.mutate(values, {
      onSuccess: (user) => {
        toast.success("Обліковий запис створено");
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
      <div className="grid gap-2">
        <Label htmlFor="new-password">Тимчасовий пароль</Label>
        <div className="flex gap-2">
          <Input
            id="new-password"
            value={values.password}
            onChange={set("password")}
            aria-invalid={!!errors.password}
            autoComplete="new-password"
            className="h-10 bg-sheet font-mono"
            required
          />
          <Button
            type="button"
            variant="outline"
            className="h-10"
            onClick={() => setValues((v) => ({ ...v, password: generatePassword() }))}
          >
            Згенерувати
          </Button>
        </div>
        {errors.password ? (
          <p className="text-sm text-destructive">{errors.password}</p>
        ) : (
          <p className="text-xs text-slate">
            Передайте пароль людині захищеним каналом. Нові акаунти отримують базову роль
            «Employee».
          </p>
        )}
      </div>
      <span className="flex gap-2">
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Створюємо…" : "Створити обліковий запис"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}
