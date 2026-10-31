import type { Metadata } from "next";
import { Onest, Unbounded } from "next/font/google";

import { Providers } from "./providers";
import "./globals.css";

// Обидва — від української студії, з повною кирилицею
const onest = Onest({
  subsets: ["latin", "cyrillic"],
  variable: "--font-onest",
});
const unbounded = Unbounded({
  subsets: ["latin", "cyrillic"],
  variable: "--font-unbounded",
});

export const metadata: Metadata = {
  title: { default: "Кадри", template: "%s — Кадри" },
  description: "Внутрішня HR-система: профіль, відпустки, команда, оргструктура.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className={`${onest.variable} ${unbounded.variable}`}>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
