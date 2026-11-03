import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthShell } from "../auth-shell";
import { SetPasswordForm } from "../set-password-form";

export const metadata: Metadata = { title: "Запрошення" };

export default function InvitePage() {
  return (
    <AuthShell
      title="Ласкаво просимо"
      lead="Задайте пароль — і обліковий запис готовий. Логін — ваша робоча пошта."
    >
      {/* uid і token — з адреси посилання, читаються лише на клієнті */}
      <Suspense>
        <SetPasswordForm kind="invite" />
      </Suspense>
    </AuthShell>
  );
}
