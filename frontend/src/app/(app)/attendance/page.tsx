import type { Metadata } from "next";
import { Suspense } from "react";

import { MyTimesheet } from "./my-timesheet";

export const metadata: Metadata = { title: "Мій табель" };

export default function AttendancePage() {
  // «Сьогодні» рахується на клієнті під час кожного відкриття, а не під час збірки
  return (
    <Suspense>
      <MyTimesheet />
    </Suspense>
  );
}
