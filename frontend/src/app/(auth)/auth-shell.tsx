/** Макет сторінок без сесії (вхід, скидання пароля, запрошення). */
export function AuthShell({
  title,
  lead,
  children,
  footer,
}: {
  title: string;
  lead: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
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
          <h1 className="text-[1.875rem] font-medium">{title}</h1>
          <p className="mt-2 text-slate">{lead}</p>
          {children}
          {footer && <div className="mt-10 text-sm leading-relaxed text-slate">{footer}</div>}
        </div>
      </section>
    </main>
  );
}
