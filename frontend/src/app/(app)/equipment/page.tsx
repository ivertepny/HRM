import type { Metadata } from "next";

import { EquipmentList } from "./equipment-list";

export const metadata: Metadata = { title: "Обладнання" };

export default function EquipmentPage() {
  return <EquipmentList />;
}
