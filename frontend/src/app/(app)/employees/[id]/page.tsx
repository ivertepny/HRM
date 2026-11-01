import type { Metadata } from "next";
import { Suspense } from "react";

import { EmployeeView } from "./employee-view";

export const metadata: Metadata = { title: "Працівник" };

export default function EmployeePage() {
  // id читається на клієнті (useParams) — сторінка лишається статичною оболонкою
  return (
    <Suspense>
      <EmployeeView />
    </Suspense>
  );
}
