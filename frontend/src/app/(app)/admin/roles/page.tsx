import type { Metadata } from "next";
import { Suspense } from "react";

import { RolesView } from "./roles-view";

export const metadata: Metadata = { title: "Ролі та доступ" };

export default function RolesPage() {
  return (
    <Suspense>
      <RolesView />
    </Suspense>
  );
}
