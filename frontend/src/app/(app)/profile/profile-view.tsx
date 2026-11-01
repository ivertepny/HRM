"use client";

import { EmployeeEquipment } from "@/components/app/employee-equipment";
import { Section } from "@/components/app/section";
import { Skeleton } from "@/components/ui/skeleton";
import { fullName } from "@/components/app/user-name";
import { formatDate, formatMoney, LEVEL_LABELS } from "@/lib/format";
import { useMe, useMyAccess, useMyEmployee } from "@/lib/queries";

import { NameForm } from "./name-form";

function Facts({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-[9rem_minmax(0,1fr)]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-slate">{label}</dt>
          <dd>{value ?? <span className="text-slate">не вказано</span>}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ProfileView() {
  const me = useMe();
  const access = useMyAccess();
  const employee = useMyEmployee(me.data?.id);

  if (me.isPending) {
    return (
      <div className="grid gap-6" aria-busy="true">
        <Skeleton className="h-12 w-72" />
        <Skeleton className="h-5 w-56" />
        <Skeleton className="mt-8 h-40 w-full max-w-2xl" />
      </div>
    );
  }
  if (me.isError) {
    return <p role="alert">Не вдалося завантажити профіль: {me.error.message}</p>;
  }

  const user = me.data;
  const job = employee.data;
  const unitNames = new Map(
    (access.data?.scoped ?? []).map((scope) => [scope.unit.id, scope.unit.name]),
  );

  return (
    <div className="grid gap-10">
      <header>
        <h1 className="text-[2.25rem] leading-tight font-medium md:text-[2.75rem]">
          {fullName(user)}
        </h1>
        <p className="mt-2 text-lg text-slate">
          {job ? `${job.position?.name}, ${job.structural_unit?.full_name}` : user.email}
        </p>
      </header>

      <Section title="Особисті дані">
        <NameForm user={user} />
        <p className="mt-6 text-sm text-slate">
          Пошта для входу: <span className="text-ink">{user.email}</span>. Змінити її може
          лише HR.
        </p>
      </Section>

      <Section title="Робота">
        {employee.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : job ? (
          <Facts
            rows={[
              ["Посада", job.position?.name],
              ["Підрозділ", job.structural_unit?.full_name],
              ["Рівень", job.level ? LEVEL_LABELS[job.level] : null],
              ["Працює з", formatDate(job.date_hired)],
              ...(job.date_fired
                ? ([["Звільнення", formatDate(job.date_fired)]] as [string, string | null][])
                : []),
            ]}
          />
        ) : (
          <p className="text-slate">
            Профіль працівника ще не створено — його заводить HR під час оформлення.
          </p>
        )}
      </Section>

      {job && (
        <Section title="Зарплата">
          <p className="font-heading text-[1.75rem] font-medium tabular-nums">
            {formatMoney(job.salary, job.salary_currency) ?? (
              <span className="font-sans text-base text-slate">не вказано</span>
            )}
          </p>
          <p className="mt-2 text-sm text-slate">
            Бачите лише ви та HR із доступом до зарплат.
          </p>
        </Section>
      )}

      {job && (
        <Section title="Обладнання">
          <EmployeeEquipment employeeId={job.id!} emptyText="За вами не закріплено обладнання." />
        </Section>
      )}

      <Section title="Доступ">
        {access.data?.is_superuser ? (
          <p>Адміністратор системи — повний доступ.</p>
        ) : access.data?.roles.length ? (
          <ul className="grid gap-3">
            {access.data.roles.map((role) => (
              <li key={role.id}>
                <span className="font-medium">{role.role_name}</span>
                <span className="text-slate">
                  {" — "}
                  {role.structural_unit
                    ? `у підрозділі «${unitNames.get(role.structural_unit) ?? "…"}» і дочірніх`
                    : "уся компанія"}
                  {role.expires_at && `, до ${formatDate(role.expires_at)}`}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate">Ролей немає. Свій профіль ви бачите завжди.</p>
        )}
      </Section>
    </div>
  );
}
