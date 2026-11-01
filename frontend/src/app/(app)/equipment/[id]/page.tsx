import type { Metadata } from "next";
import { Suspense } from "react";

import { ItemView } from "./item-view";

export const metadata: Metadata = { title: "Обладнання" };

export default function EquipmentItemPage() {
  // id читається на клієнті (useParams) — сторінка лишається статичною оболонкою
  return (
    <Suspense>
      <ItemView />
    </Suspense>
  );
}
