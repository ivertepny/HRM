"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, unwrap } from "@/lib/api/client";

/** Запит листа зі скиданням. Відповідь однакова, є такий запис чи ні.
 *  Поле некероване: значення читаємо з форми при відправці, тож введене ще до
 *  гідрації (повільна мережа) не губиться. */
export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const value = String(new FormData(event.currentTarget).get("email") ?? "").trim();
    if (!/^\S+@\S+\.\S+$/.test(value)) {
      setError("Введіть робочу пошту у форматі name@company.com");
      return;
    }
    setPending(true);
    try {
      await unwrap(api.POST("/api/users/password-reset/", { body: { email: value } }));
      setSentTo(value);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setPending(false);
    }
  }

  if (sentTo) {
    return (
      <div role="status" className="mt-8 grid gap-3 rounded-md bg-mist p-4">
        <p className="font-medium">Перевірте пошту</p>
        <p className="text-sm text-slate">
          Якщо для {sentTo} є обліковий запис, ми надіслали лист із посиланням. Воно діє 2
          години. Лист не прийшов — перевірте «Спам» або зверніться до HR.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="mt-8 grid gap-5">
      <div className="grid gap-2">
        <Label htmlFor="email">Робоча пошта</Label>
        <Input
          id="email"
          type="email"
          autoComplete="username"
          name="email"
          autoFocus
          aria-invalid={!!error}
          aria-describedby={error ? "email-error" : undefined}
          className="h-11 bg-sheet"
        />
        {error && (
          <p id="email-error" role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
      <Button type="submit" size="lg" disabled={pending} className="h-11 text-base">
        {pending ? "Надсилаємо…" : "Надіслати посилання"}
      </Button>
    </form>
  );
}
