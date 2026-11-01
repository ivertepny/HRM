const dateFormat = new Intl.DateTimeFormat("uk-UA", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function formatDate(value?: string | null) {
  if (!value) return null;
  // "2025-03-01" — календарна дата без часової зони; не зсуваємо її в UTC
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return dateFormat.format(new Date(year, month - 1, day));
}

export function formatMoney(amount?: string | null, currency = "UAH") {
  if (amount == null) return null;
  return new Intl.NumberFormat("uk-UA", { style: "currency", currency }).format(
    Number(amount),
  );
}

export const LEVEL_LABELS: Record<string, string> = {
  trainee: "Trainee",
  junior: "Junior",
  middle: "Middle",
  senior: "Senior",
};

/** Українська множина: plural(3, ["працівник", "працівники", "працівників"]) → "працівники". */
export function plural(count: number, [one, few, many]: [string, string, string]) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export const UNITS: [string, string, string] = ["підрозділ", "підрозділи", "підрозділів"];
export const PEOPLE: [string, string, string] = ["працівник", "працівники", "працівників"];
