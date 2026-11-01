"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import {
  sessionNameFrom,
  useChatMessages,
  useChatSessions,
  useDeleteSession,
  useRenameSession,
  useSendMessage,
} from "@/lib/chat-queries";
import { formatDate } from "@/lib/format";
import { useMyAccess } from "@/lib/queries";
import { cn } from "@/lib/utils";

import { Composer } from "./composer";
import { Transcript } from "./transcript";

const SUGGESTIONS = [
  "Покажи структуру нашої компанії",
  "Як подати заявку на відпустку?",
  "Які документи потрібні для лікарняного?",
];

export function AssistantView() {
  const access = useMyAccess();
  const allowed = canAnywhere(access.data, "ai:use");

  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const sessionId = params.get("session") ?? undefined;
  const [error, setError] = useState<string | null>(null);
  const select = (id?: string) => {
    setError(null); // помилка стосувалась попередньої розмови
    router.replace(id ? `${pathname}?session=${id}` : pathname, { scroll: false });
  };

  const sessions = useChatSessions();
  const messages = useChatMessages(sessionId);
  const send = useSendMessage();

  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string>();
  const endRef = useRef<HTMLDivElement>(null);

  const exchanges = sessionId ? (messages.data ?? []) : [];
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [exchanges.length, pendingQuestion]);

  async function ask(question: string) {
    setError(null);
    setPendingQuestion(question);
    setDraft("");
    try {
      const result = await send.mutateAsync({
        message: question,
        ...(sessionId
          ? { session_id: sessionId }
          : { chat_session_name: sessionNameFrom(question) }),
      });
      if (result.session_id !== sessionId) select(result.session_id);
    } catch (err) {
      // Питання не губимо — його можна надіслати ще раз
      setDraft(question);
      setError((err as Error).message);
    } finally {
      setPendingQuestion(undefined);
    }
  }

  if (access.isSuccess && !allowed) {
    return (
      <div className="grid gap-4">
        <PageHeader title="AI-асистент" />
        <p className="text-slate">Асистент доступний з дозволом ai:use — зверніться до HR.</p>
      </div>
    );
  }

  const current = sessions.data?.find((s) => s.session_id === sessionId);

  return (
    <div className="grid gap-8">
      <PageHeader title="AI-асистент">
        Відповідає на HR-питання; про структуру компанії — з урахуванням ваших прав.
      </PageHeader>

      <div className="grid gap-8 border-t border-border pt-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-12">
        <aside className="grid content-start gap-3" aria-label="Розмови">
          <div>
            <Button variant="outline" onClick={() => select(undefined)} disabled={!sessionId}>
              Нова розмова
            </Button>
          </div>
          {sessions.isPending ? (
            <Skeleton className="h-32 w-full" />
          ) : sessions.data?.length ? (
            <ul className="grid gap-px">
              {sessions.data.map((s) => {
                const active = s.session_id === sessionId;
                return (
                  <li key={s.session_id}>
                    <button
                      type="button"
                      onClick={() => select(s.session_id)}
                      aria-current={active ? "true" : undefined}
                      className={cn(
                        "w-full rounded-sm px-3 py-2 text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                        active ? "bg-ink text-mist" : "hover:bg-mist",
                      )}
                    >
                      <span className="block truncate text-[0.9375rem]">{s.name || "Без назви"}</span>
                      <span className={cn("block text-xs", active ? "text-mist/70" : "text-slate")}>
                        {formatDate(s.updated_at)}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-slate">Розмов ще немає.</p>
          )}
        </aside>

        <section className="grid min-w-0 content-start gap-6" aria-label="Розмова">
          {current && (
            <SessionHeader
              key={current.session_id}
              sessionId={current.session_id!}
              name={current.name || "Без назви"}
              onDeleted={() => select(undefined)}
            />
          )}

          {sessionId && messages.isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : exchanges.length === 0 && !pendingQuestion ? (
            <div className="grid gap-3">
              <p className="text-slate">Почніть з власного питання або оберіть приклад:</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    disabled={send.isPending}
                    onClick={() => ask(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <Transcript exchanges={exchanges} pendingQuestion={pendingQuestion} />
          )}

          {error && (
            <p role="alert" className="rounded-md bg-mist p-3 text-sm text-destructive">
              {error} Питання збережено в полі нижче — надішліть його ще раз.
            </p>
          )}

          <div ref={endRef} className="sticky bottom-4">
            <Composer
              value={draft}
              onChange={setDraft}
              pending={send.isPending}
              onSend={() => ask(draft.trim())}
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function SessionHeader({
  sessionId,
  name,
  onDeleted,
}: {
  sessionId: string;
  name: string;
  onDeleted: () => void;
}) {
  const rename = useRenameSession();
  const remove = useDeleteSession();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const [confirming, setConfirming] = useState(false);

  async function saveName(event: React.FormEvent) {
    event.preventDefault();
    try {
      await rename.mutateAsync({ sessionId, name: value.trim() || "Без назви" });
      setEditing(false);
    } catch (error) {
      toast.error((error as Error).message);
    }
  }

  async function destroy() {
    try {
      await remove.mutateAsync(sessionId);
    } catch (error) {
      toast.error((error as Error).message);
      return;
    }
    toast.success("Розмову видалено");
    onDeleted();
  }

  if (editing) {
    return (
      <form onSubmit={saveName} className="flex flex-wrap items-center gap-2">
        <label htmlFor="session-name" className="sr-only">
          Назва розмови
        </label>
        <Input
          id="session-name"
          autoFocus
          maxLength={255}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="h-9 max-w-md"
        />
        <Button type="submit" size="sm" disabled={rename.isPending}>
          Зберегти назву
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
          Скасувати
        </Button>
      </form>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 className="font-sans text-lg font-semibold">{name}</h2>
      {confirming ? (
        <span className="flex items-center gap-2 text-sm">
          Видалити розмову разом з усіма відповідями?
          <Button size="sm" variant="destructive" disabled={remove.isPending} onClick={destroy}>
            Видалити розмову
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
            Не видаляти
          </Button>
        </span>
      ) : (
        <span className="flex gap-1">
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
            Перейменувати
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setConfirming(true)}>
            Видалити розмову
          </Button>
        </span>
      )}
    </div>
  );
}
