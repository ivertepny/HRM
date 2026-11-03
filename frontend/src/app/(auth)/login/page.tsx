import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AuthShell } from "../auth-shell";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Вхід" };

export default function LoginPage() {
  return (
    <AuthShell
      title="Вхід"
      lead="Увійдіть з робочою поштою."
      footer={
        <>
          <p>
            <Link href="/forgot-password" className="text-primary underline-offset-4 hover:underline">
              Забули пароль?
            </Link>
          </p>
          <p className="mt-3">
            Облікові записи створює відділ кадрів — нові працівники отримують запрошення на
            пошту.
          </p>
        </>
      }
    >
      {/* useSearchParams (повернення на ?next) рендериться лише на клієнті */}
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
