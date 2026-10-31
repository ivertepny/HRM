import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Вхід" };

export default function LoginPage() {
  return (
    <main className="grid min-h-dvh md:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
      <section
        aria-label="Кадри"
        className="flex flex-col justify-between bg-ink px-6 py-8 text-mist md:px-12 md:py-14"
      >
        <p
          className="font-heading leading-[0.9] font-semibold tracking-[-0.03em]"
          style={{ fontSize: "clamp(3.25rem, 9vw, 8.5rem)" }}
        >
          Кадри
        </p>
        <p className="mt-6 max-w-[34ch] text-lg leading-relaxed text-mist/75 md:text-xl">
          Профіль, відпустки, команда й оргструктура компанії — в одному місці.
        </p>
      </section>

      <section className="flex items-center px-6 py-12 md:px-16">
        <div className="w-full max-w-sm">
          <h1 className="text-[1.875rem] font-medium">Вхід</h1>
          <p className="mt-2 text-slate">Увійдіть з робочою поштою.</p>
          {/* useSearchParams (повернення на ?next) рендериться лише на клієнті */}
          <Suspense>
            <LoginForm />
          </Suspense>
          <p className="mt-10 text-sm leading-relaxed text-slate">
            Облікові записи створює відділ кадрів. Немає доступу або забули
            пароль — зверніться до HR.
          </p>
        </div>
      </section>
    </main>
  );
}
