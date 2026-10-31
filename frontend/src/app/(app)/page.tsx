import { redirect } from "next/navigation";

// Поки єдиний готовий розділ — профіль; згодом тут буде головна
export default function HomePage() {
  redirect("/profile");
}
