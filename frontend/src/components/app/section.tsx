/** Розділ сторінки: назва зліва, вміст справа (на мобільних — одне під одним). */
export function Section({
  title,
  children,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  /** Таблиці й календар — на всю ширину, без обмеження довжини рядка. */
  wide?: boolean;
}) {
  return (
    <section className="grid gap-4 border-t border-border pt-8 md:grid-cols-[11rem_minmax(0,1fr)] md:gap-10">
      <h2 className="font-sans text-[0.9375rem] font-semibold">{title}</h2>
      <div className={wide ? "min-w-0" : "max-w-[40rem]"}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <header>
      <h1 className="text-[2.25rem] leading-tight font-medium md:text-[2.75rem]">{title}</h1>
      {children && <div className="mt-2 text-lg text-slate">{children}</div>}
    </header>
  );
}
