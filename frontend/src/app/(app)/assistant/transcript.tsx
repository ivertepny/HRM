"use client";

import { TOOL_NOTES, type Exchange } from "@/lib/chat-queries";

const time = new Intl.DateTimeFormat("uk-UA", { hour: "2-digit", minute: "2-digit" });

/**
 * Розмова як стенограма: питання — з чорнильною лінією зліва, відповідь —
 * звичайним текстом під ним. Для довідок це читається краще за «бульбашки».
 */
export function Transcript({
  exchanges,
  pendingQuestion,
}: {
  exchanges: Exchange[];
  pendingQuestion?: string;
}) {
  return (
    <ol className="grid gap-8" aria-live="polite">
      {exchanges.map((exchange) => (
        <li key={exchange.id} className="grid gap-3">
          <Question text={exchange.message} at={exchange.created_at} />
          <div className="max-w-[68ch] text-[0.9375rem] leading-relaxed whitespace-pre-wrap">
            {exchange.response}
          </div>
          {exchange.tools_used?.map(
            (tool) =>
              TOOL_NOTES[tool] && (
                <p key={tool} className="text-xs text-slate">
                  {TOOL_NOTES[tool]}
                </p>
              ),
          )}
        </li>
      ))}
      {pendingQuestion && (
        <li className="grid gap-3">
          <Question text={pendingQuestion} />
          <p className="text-slate" role="status">
            <span className="inline-block animate-pulse">Асистент готує відповідь…</span>
          </p>
        </li>
      )}
    </ol>
  );
}

function Question({ text, at }: { text: string; at?: string }) {
  return (
    <div className="border-l-2 border-ink pl-4">
      <p className="text-xs text-slate">Ви{at && `, ${time.format(new Date(at))}`}</p>
      <p className="mt-0.5 font-medium whitespace-pre-wrap">{text}</p>
    </div>
  );
}
