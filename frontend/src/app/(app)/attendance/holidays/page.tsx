import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { HolidayManager } from "./holiday-manager";

export const metadata: Metadata = { title: "Святкові дні" };

export default function HolidaysPage() {
  return (
    // Поточний рік рахується на клієнті — під час збірки його не знати
    <Suspense fallback={<Skeleton className="h-64 w-full max-w-2xl" />}>
      <HolidayManager />
    </Suspense>
  );
}
