import type { Metadata } from "next";
import { Suspense } from "react";

import { OrgView } from "./org-view";

export const metadata: Metadata = { title: "Оргструктура" };

export default function CompanyPage() {
  // ?unit= читається на клієнті (useSearchParams) — потрібна межа Suspense
  return (
    <Suspense>
      <OrgView />
    </Suspense>
  );
}
