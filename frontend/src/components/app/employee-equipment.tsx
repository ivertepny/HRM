"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { CATEGORY_LABELS } from "@/lib/equipment";
import { formatDate } from "@/lib/format";
import { useAssignments } from "@/lib/queries";

/** Що зараз на руках у працівника. linkItems — посилання на картки (з equipment:read). */
export function EmployeeEquipment({
  employeeId,
  linkItems = false,
  emptyText = "Обладнання не видавалось.",
}: {
  employeeId: number;
  linkItems?: boolean;
  emptyText?: string;
}) {
  const assignments = useAssignments({ employee: employeeId, active: true });

  if (assignments.isPending) return <Skeleton className="h-16 w-full" />;
  if (assignments.isError) {
    return <p role="alert">Не вдалося завантажити обладнання: {assignments.error.message}</p>;
  }
  if (assignments.data.length === 0) return <p className="text-slate">{emptyText}</p>;

  return (
    <ul className="grid gap-3">
      {assignments.data.map(({ id, equipment, date_assigned }) => (
        <li key={id}>
          {linkItems ? (
            <Link
              href={`/equipment/${equipment?.id}`}
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              {equipment?.name}
            </Link>
          ) : (
            <span className="font-medium">{equipment?.name}</span>
          )}
          <span className="block text-sm text-slate">
            {CATEGORY_LABELS[equipment?.category ?? "other"]} ·{" "}
            <span className="font-mono">{equipment?.serial_number}</span> · з{" "}
            {formatDate(date_assigned)}
          </span>
        </li>
      ))}
    </ul>
  );
}
