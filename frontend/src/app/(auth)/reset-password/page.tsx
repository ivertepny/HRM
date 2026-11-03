import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthShell } from "../auth-shell";
import { SetPasswordForm } from "../set-password-form";

export const metadata: Metadata = { title: "Новий пароль" };

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Новий пароль" lead="Задайте новий пароль до облікового запису.">
      {/* uid і token — з адреси посилання, читаються лише на клієнті */}
      <Suspense>
        <SetPasswordForm kind="reset" />
      </Suspense>
    </AuthShell>
  );
}
