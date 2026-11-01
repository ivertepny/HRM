import type { Metadata } from "next";
import { Suspense } from "react";

import { AssistantView } from "./assistant-view";

export const metadata: Metadata = { title: "AI-асистент" };

export default function AssistantPage() {
  return (
    <Suspense>
      <AssistantView />
    </Suspense>
  );
}
