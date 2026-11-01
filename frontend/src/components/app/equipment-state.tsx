import { STATE_LABELS, type EquipmentState } from "@/lib/equipment";
import { cn } from "@/lib/utils";

const DOT: Record<EquipmentState, string> = {
  in_stock: "bg-warning",
  assigned: "bg-primary",
  written_off: "bg-slate/50",
};

export function EquipmentStateTag({ state }: { state: EquipmentState }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap",
        state === "written_off" && "text-slate",
      )}
    >
      <span aria-hidden className={cn("size-2 rounded-full", DOT[state])} />
      {STATE_LABELS[state]}
    </span>
  );
}
