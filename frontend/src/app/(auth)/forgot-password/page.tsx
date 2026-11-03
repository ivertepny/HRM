import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "../auth-shell";
import { ForgotPasswordForm } from "./forgot-password-form";

export const metadata: Metadata = { title: "Скидання пароля" };

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      title="Забули пароль?"
      lead="Надішлемо на робочу пошту посилання, щоб задати новий."
      footer={
        <Link href="/login" className="text-primary underline-offset-4 hover:underline">
          Повернутися до входу
        </Link>
      }
    >
      <ForgotPasswordForm />
    </AuthShell>
  );
}
