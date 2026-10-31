import type { Metadata } from "next";

import { ReviewView } from "./review-view";

export const metadata: Metadata = { title: "Відпустки команди" };

export default function VacationReviewPage() {
  return <ReviewView />;
}
