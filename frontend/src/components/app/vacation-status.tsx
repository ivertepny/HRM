import { cn } from "@/lib/utils";
import { STATUS_LABELS, type VacationStatus } from "@/lib/vacations";

const DOT: Record<VacationStatus, string> = {
  pending: "bg-warning",
  approved: "bg-primary",
  rejected: "bg-destructive",
  cancelled: "bg-slate/50",
};

export function VacationStatusTag({ status }: { status: VacationStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap",
        status === "cancelled" && "text-slate",
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", DOT[status])} />
      {STATUS_LABELS[status]}
    </span>
  );
}
