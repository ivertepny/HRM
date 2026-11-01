import type { Metadata } from "next";
import { Suspense } from "react";

import { EmployeeDirectory } from "./employee-directory";

export const metadata: Metadata = { title: "Працівники" };

export default function EmployeesPage() {
  return (
    <Suspense>
      <EmployeeDirectory />
    </Suspense>
  );
}
