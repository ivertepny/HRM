"use client";

import { toast } from "sonner";

import { PageHeader, Section } from "@/components/app/section";
import { VacationStatusTag } from "@/components/app/vacation-status";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe, useMyEmployee, useVacationAction, useVacations } from "@/lib/queries";
import {
  annualDaysUsed,
  dayWord,
  formatRange,
  isCancellable,
  TYPE_LABELS,
  type Vacation,
} from "@/lib/vacations";

import { VacationForm } from "./vacation-form";

export function MyVacations() {
  const me = useMe();
  const employee = useMyEmployee(me.data?.id);
  const employeeId = employee.data?.id;
  const vacations = useVacations({ employee: employeeId }, employeeId !== undefined);

  if (me.isPending || employee.isPending) {
    return <Skeleton className="h-12 w-80" aria-busy="true" />;
  }
  if (!employee.data) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Мої відпустки" />
        <p className="max-w-[60ch] text-slate">
          Подавати заявки можна після оформлення профілю працівника. Його створює HR —
          зверніться до відділу кадрів.
        </p>
      </div>
    );
  }

  const year = new Date().getFullYear();
  const used = annualDaysUsed(vacations.data ?? [], year);

  return (
    <div className="grid gap-10">
      <PageHeader title="Мої відпустки">
        {vacations.isSuccess &&
          `Щорічна відпустка у ${year}: використано ${used} ${dayWord(used)}.`}
      </PageHeader>

      <Section title="Нова заявка">
        <VacationForm />
      </Section>

      <Section title="Заявки" wide>
        {vacations.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : vacations.isError ? (
          <p role="alert">Не вдалося завантажити заявки: {vacations.error.message}</p>
        ) : vacations.data.length === 0 ? (
          <p className="text-slate">Заявок ще немає. Подайте першу у формі вище.</p>
        ) : (
          <VacationTable vacations={vacations.data} />
        )}
      </Section>
    </div>
  );
}

function VacationTable({ vacations }: { vacations: Vacation[] }) {
  const action = useVacationAction();

  function cancel(vacation: Vacation) {
    action.mutate(
      { id: vacation.id!, action: "cancel" },
      {
        onSuccess: () => toast.success("Заявку скасовано"),
        onError: (error) => toast.error(error.message),
      },
    );
  }

  return (
    <table className="w-full border-collapse text-left">
      <caption className="sr-only">Мої заявки на відпустку</caption>
      <thead className="text-sm text-slate">
        <tr className="hidden md:table-row">
          <th className="pb-3 font-normal">Період</th>
          <th className="pb-3 font-normal">Тип</th>
          <th className="pb-3 font-normal">Статус</th>
          <th className="pb-3 font-normal">
            <span className="sr-only">Дії</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {vacations.map((vacation) => (
          <tr
            key={vacation.id}
            className="grid gap-1 border-t border-border py-4 md:table-row md:py-0"
          >
            <td className="md:py-4 md:pr-6">
              <span className="font-medium">{formatRange(vacation.date_start, vacation.date_end)}</span>
              <span className="block text-sm text-slate">
                {vacation.days} {dayWord(vacation.days ?? 0)}
              </span>
            </td>
            <td className="md:py-4 md:pr-6">
              {TYPE_LABELS[vacation.vacation_type ?? "annual"]}
              {vacation.comment && (
                <span className="block text-sm text-slate">{vacation.comment}</span>
              )}
            </td>
            <td className="md:py-4 md:pr-6">
              <VacationStatusTag status={vacation.status!} />
              {vacation.decision_comment && (
                <span className="block text-sm text-slate">«{vacation.decision_comment}»</span>
              )}
            </td>
            <td className="md:py-4 md:text-right">
              {isCancellable(vacation) && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={action.isPending}
                  onClick={() => cancel(vacation)}
                >
                  Скасувати заявку
                </Button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
