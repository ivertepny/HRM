import type { Metadata } from "next";
import { Suspense } from "react";

import { TeamReport } from "./team-report";

export const metadata: Metadata = { title: "Табель команди" };

export default function AttendanceReportPage() {
  // «Сьогодні» рахується на клієнті під час кожного відкриття, а не під час збірки
  return (
    <Suspense>
      <TeamReport />
    </Suspense>
  );
}
