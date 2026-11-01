import type { Metadata } from "next";

import { EmployeeDirectory } from "./employee-directory";

export const metadata: Metadata = { title: "Працівники" };

export default function EmployeesPage() {
  return <EmployeeDirectory />;
}
