import type { Schemas } from "@/lib/api/client";

export function fullName(user?: Pick<Schemas["User"], "first_name" | "last_name" | "email">) {
  if (!user) return "";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return name || user.email || "";
}

export function initials(user?: Pick<Schemas["User"], "first_name" | "last_name" | "email">) {
  if (!user) return "";
  const letters = [user.first_name, user.last_name]
    .filter(Boolean)
    .map((part) => part!.trim()[0]);
  return (letters.join("") || user.email?.[0] || "?").toUpperCase();
}
