import type { Metadata } from "next";

import { MyVacations } from "./my-vacations";

export const metadata: Metadata = { title: "Мої відпустки" };

export default function VacationsPage() {
  return <MyVacations />;
}
