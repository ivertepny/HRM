"use client";

import { useRef } from "react";

import { Button } from "@/components/ui/button";

/** Поле питання: Enter — надіслати, Shift+Enter — новий рядок. */
export function Composer({
  value,
  onChange,
  onSend,
  pending,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  pending: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !pending;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSend) onSend();
      }}
      className="grid gap-2 rounded-lg border border-input bg-sheet p-3 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30"
    >
      <label htmlFor="question" className="sr-only">
        Питання асистенту
      </label>
      <textarea
        id="question"
        ref={ref}
        rows={2}
        maxLength={4000}
        value={value}
        placeholder="Запитайте про відпустки, документи чи структуру компанії"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (canSend) onSend();
          }
        }}
        className="max-h-48 min-h-12 w-full resize-y bg-transparent text-[0.9375rem] outline-none placeholder:text-slate"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-slate">Enter — надіслати, Shift+Enter — новий рядок</span>
        <Button type="submit" size="sm" disabled={!canSend}>
          {pending ? "Асистент відповідає…" : "Надіслати"}
        </Button>
      </div>
    </form>
  );
}
