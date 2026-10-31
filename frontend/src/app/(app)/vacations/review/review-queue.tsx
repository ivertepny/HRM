"use client";

import { Fragment, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useVacationAction, useVacations } from "@/lib/queries";
import { calendarDays, formatRange, TYPE_LABELS, type Vacation } from "@/lib/vacations";

export function ReviewQueue({ myEmployeeId }: { myEmployeeId?: number }) {
  const pending = useVacations({ status: "pending" });
  const action = useVacationAction();
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [reason, setReason] = useState("");

  if (pending.isPending) return <Skeleton className="h-40 w-full" />;
  if (pending.isError) {
    return <p role="alert">Не вдалося завантажити заявки: {pending.error.message}</p>;
  }

  const queue = [...pending.data].sort((a, b) => a.date_start.localeCompare(b.date_start));
  if (queue.length === 0) {
    return <p className="text-slate">Усі заявки розглянуто. Нові з&apos;являться тут.</p>;
  }

  function decide(vacation: Vacation, decision: "approve" | "reject") {
    action.mutate(
      { id: vacation.id!, action: decision, comment: decision === "reject" ? reason : "" },
      {
        onSuccess: () => {
          toast.success(decision === "approve" ? "Заявку схвалено" : "Заявку відхилено");
          setRejecting(null);
          setReason("");
        },
        onError: (error) => toast.error(error.message),
      },
    );
  }

  return (
    <table className="w-full border-collapse text-left">
      <caption className="sr-only">Заявки на розгляді, найближчі першими</caption>
      <thead className="text-sm text-slate">
        <tr className="hidden md:table-row">
          <th className="pb-3 font-normal">Працівник</th>
          <th className="pb-3 font-normal">Період</th>
          <th className="pb-3 font-normal">Тип</th>
          <th className="pb-3 font-normal">
            <span className="sr-only">Рішення</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {queue.map((vacation) => {
          const own = vacation.employee?.id === myEmployeeId;
          return (
            <Fragment key={vacation.id}>
              <tr className="grid gap-1 border-t border-border py-4 md:table-row md:py-0">
                <td className="font-medium md:py-4 md:pr-6">{vacation.employee?.name}</td>
                <td className="md:py-4 md:pr-6">
                  {formatRange(vacation.date_start, vacation.date_end)}
                  <span className="block text-sm text-slate">
                    {calendarDays(vacation.days ?? 0)}
                  </span>
                </td>
                <td className="md:py-4 md:pr-6">
                  {TYPE_LABELS[vacation.vacation_type ?? "annual"]}
                  {vacation.comment && (
                    <span className="block text-sm text-slate">«{vacation.comment}»</span>
                  )}
                </td>
                <td className="md:py-4 md:text-right">
                  {own ? (
                    <span className="text-sm text-slate">Власну заявку розглядає інший HR</span>
                  ) : (
                    <span className="inline-flex gap-2">
                      <Button
                        size="sm"
                        disabled={action.isPending}
                        onClick={() => decide(vacation, "approve")}
                      >
                        Схвалити
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-expanded={rejecting === vacation.id}
                        onClick={() => {
                          setRejecting(rejecting === vacation.id ? null : vacation.id!);
                          setReason("");
                        }}
                      >
                        Відхилити
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
              {rejecting === vacation.id && (
                <tr className="block md:table-row">
                  <td colSpan={4} className="block pb-5 md:table-cell">
                    <div className="grid max-w-xl gap-2 rounded-md bg-mist p-4">
                      <Label htmlFor={`reason-${vacation.id}`}>
                        Причина відмови — її побачить працівник
                      </Label>
                      <Textarea
                        id={`reason-${vacation.id}`}
                        rows={2}
                        maxLength={500}
                        autoFocus
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="bg-sheet"
                      />
                      <span className="flex gap-2">
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={action.isPending}
                          onClick={() => decide(vacation, "reject")}
                        >
                          Відхилити заявку
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setRejecting(null)}>
                          Не відхиляти
                        </Button>
                      </span>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
