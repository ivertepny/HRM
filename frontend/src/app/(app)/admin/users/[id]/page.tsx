import type { Metadata } from "next";
import { Suspense } from "react";

import { UserView } from "./user-view";

export const metadata: Metadata = { title: "Обліковий запис" };

export default function UserPage() {
  return (
    <Suspense>
      <UserView />
    </Suspense>
  );
}
