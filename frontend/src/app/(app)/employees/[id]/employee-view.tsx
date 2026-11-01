"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { EmployeeEquipment } from "@/components/app/employee-equipment";
import { PageHeader, Section } from "@/components/app/section";
import { fullName, initials } from "@/components/app/user-name";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { ApiError } from "@/lib/api/client";
import { fileHref, isFired } from "@/lib/employees";
import { formatDate, formatMoney, LEVEL_LABELS } from "@/lib/format";
import { useEmployee, useMe, useMyAccess } from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

import { CareerLog } from "./career-log";
import { DismissForm } from "./dismiss-form";
import { DocumentsSection } from "./documents-section";
import { StaffChangeForm } from "./staff-change-form";

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

export function EmployeeView() {
  const { id } = useParams<{ id: string }>();
  const employeeId = Number(id);
  const employee = useEmployee(employeeId);
  const access = useMyAccess();
  const me = useMe();

  if (employee.isPending) {
    return (
      <div className="grid gap-6" aria-busy="true">
        <Skeleton className="h-12 w-80" />
        <Skeleton className="h-40 w-full max-w-2xl" />
      </div>
    );
  }
  if (employee.isError) {
    const notFound = employee.error instanceof ApiError && employee.error.status === 404;
    return (
      <div className="grid gap-4">
        <PageHeader title={notFound ? "Працівника не знайдено" : "Не вдалося завантажити"} />
        <p className="text-slate">
          {notFound
            ? "Його немає або він поза вашою областю доступу."
            : employee.error.message}{" "}
          <Link href="/employees" className="text-primary underline-offset-4 hover:underline">
            До списку працівників
          </Link>
        </p>
      </div>
    );
  }

  const data = employee.data;
  const isMe = data.user?.id === me.data?.id;
  const fired = isFired(data, todayISO());
  const can = (codename: string) => canAnywhere(access.data, codename);
  const canEdit = can("employees:write") && !isMe && !fired;

  return (
    <div className="grid gap-10">
      <div className="flex items-start gap-5">
        <Avatar className="size-16 shrink-0">
          {data.photo && <AvatarImage src={fileHref(data.photo)} alt="" />}
          <AvatarFallback className="bg-ink text-lg text-mist">{initials(data.user)}</AvatarFallback>
        </Avatar>
        <PageHeader title={fullName(data.user)}>
          {data.position?.name}, {data.structural_unit?.full_name}
          {data.date_fired && (
            <span className="mt-1 block text-base text-destructive">
              {fired ? "Звільнений(-а)" : "Звільнення"} {formatDate(data.date_fired)}
            </span>
          )}
        </PageHeader>
      </div>

      <Section title="Робота">
        <Facts
          rows={[
            ["Посада", data.position?.name],
            ["Підрозділ", data.structural_unit?.full_name],
            ["Рівень", data.level ? LEVEL_LABELS[data.level] : null],
            ["Працює з", formatDate(data.date_hired)],
            ["Дата народження", formatDate(data.birth_date)],
            ["Пошта", data.user?.email],
          ]}
        />
      </Section>

      {"salary" in data && (
        <Section title="Зарплата">
          <p className="font-heading text-[1.75rem] font-medium tabular-nums">
            {formatMoney(data.salary, data.salary_currency) ?? (
              <span className="font-sans text-base text-slate">не вказано</span>
            )}
          </p>
        </Section>
      )}

      {canEdit && (
        <Section title="Кадрова зміна">
          <StaffChangeForm
            employee={data}
            canEditSalary={can("salary:write")}
            canChangeUnit={can("company:read")}
          />
        </Section>
      )}

      <Section title="Кадровий журнал">
        <CareerLog employeeId={employeeId} />
      </Section>

      <Section title="Документи">
        <DocumentsSection
          employeeId={employeeId}
          canUpload={can("documents:write")}
          canDelete={can("documents:delete")}
        />
      </Section>

      {(isMe || can("equipment:read")) && (
        <Section title="Обладнання">
          <EmployeeEquipment employeeId={employeeId} linkItems={can("equipment:read")} />
          {data.date_fired && can("equipment:manage") && (
            <p className="mt-3 text-sm text-slate">
              Перед останнім робочим днем поверніть обладнання на склад.
            </p>
          )}
        </Section>
      )}

      {/* Звільнення вже призначене — повторно не оформлюємо */}
      {canEdit && !data.date_fired && (
        <Section title="Звільнення">
          <DismissForm employee={data} />
        </Section>
      )}
    </div>
  );
}
