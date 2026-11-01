"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { monthLabel, shiftMonth } from "@/lib/attendance";

/** «‹ листопад 2026 р. ›»; наперед далі поточного місяця не гортаємо. */
export function MonthSwitcher({
  month,
  max,
  onChange,
}: {
  month: string;
  max?: string;
  onChange: (month: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Попередній місяць"
        onClick={() => onChange(shiftMonth(month, -1))}
      >
        <ChevronLeft />
      </Button>
      <span className="min-w-40 text-center font-medium" aria-live="polite">
        {monthLabel(month)}
      </span>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Наступний місяць"
        disabled={max !== undefined && month >= max}
        onClick={() => onChange(shiftMonth(month, 1))}
      >
        <ChevronRight />
      </Button>
    </div>
  );
}
