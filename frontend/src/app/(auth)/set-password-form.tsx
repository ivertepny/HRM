"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, unwrap } from "@/lib/api/client";

const ENDPOINTS = {
  reset: "/api/users/password-reset/confirm/",
  invite: "/api/users/invite/accept/",
} as const;

const LINK_CLASS = "text-primary underline-offset-4 hover:underline";

/** Новий пароль за посиланням з листа (?uid=…&token=…). Поля некеровані —
 *  значення читаємо з форми при відправці (введене до гідрації не губиться). */
export function SetPasswordForm({ kind }: { kind: keyof typeof ENDPOINTS }) {
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [linkError, setLinkError] = useState<string | null>(
    uid && token ? null : "Посилання неповне. Відкрийте його з листа ще раз.",
  );
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirm = String(form.get("confirm") ?? "");
    const local: Record<string, string> = {};
    if (!password) local.password = "Введіть пароль";
    else if (password !== confirm) local.confirm = "Паролі не збігаються";
    setErrors(local);
    if (Object.keys(local).length) return;

    setPending(true);
    try {
      await unwrap(api.POST(ENDPOINTS[kind], { body: { uid, token, password } }));
      setDone(true);
    } catch (e) {
      if (!(e instanceof ApiError)) throw e;
      const fields = e.fieldErrors;
      if (fields.token || fields.uid) setLinkError(fields.token ?? fields.uid);
      else if (fields.password) setErrors({ password: fields.password });
      else setErrors({ form: e.message });
    } finally {
      setPending(false);
    }
  }

  if (done) {
    return (
      <div role="status" className="mt-8 grid gap-4 rounded-md bg-mist p-4">
        <p className="font-medium">Пароль збережено</p>
        <p className="text-sm text-slate">
          {kind === "invite"
            ? "Обліковий запис готовий — увійдіть з робочою поштою і новим паролем."
            : "Увійдіть з новим паролем. Сесії на інших пристроях завершено."}
        </p>
        <Link href="/login" className={buttonVariants({ className: "w-fit" })}>
          Увійти
        </Link>
      </div>
    );
  }

  if (linkError) {
    return (
      <div role="alert" className="mt-8 grid gap-3 rounded-md bg-mist p-4">
        <p className="font-medium">Посилання не діє</p>
        <p className="text-sm text-slate">{linkError}</p>
        <p className="text-sm text-slate">
          {kind === "invite" ? "Попросіть HR надіслати запрошення ще раз або " : "Можна "}
          <Link href="/forgot-password" className={LINK_CLASS}>
            запросити нове посилання
          </Link>
          .
        </p>
      </div>
    );
  }

  const field = (id: string, label: string, hint?: string) => (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="password"
        name={id}
        autoComplete="new-password"
        aria-invalid={!!errors[id]}
        aria-describedby={errors[id] ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className="h-11 bg-sheet"
      />
      {errors[id] ? (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {errors[id]}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-xs text-slate">
            {hint}
          </p>
        )
      )}
    </div>
  );

  return (
    <form onSubmit={submit} noValidate className="mt-8 grid gap-5">
      {field(
        "password",
        "Новий пароль",
        "Щонайменше 8 символів; не лише цифри і не схожий на пошту.",
      )}
      {field("confirm", "Повторіть пароль")}
      {errors.form && (
        <p role="alert" className="text-sm text-destructive">
          {errors.form}
        </p>
      )}
      <Button type="submit" size="lg" disabled={pending} className="h-11 text-base">
        {pending ? "Зберігаємо…" : "Зберегти пароль"}
      </Button>
    </form>
  );
}
