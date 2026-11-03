"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useResendInvite } from "@/lib/admin-queries";

/** Людина ще не задала пароль: запрошення не прийнято або посилання застаріло. */
export function InviteNotice({
  userId,
  email,
  canResend,
}: {
  userId: number;
  email: string;
  canResend: boolean;
}) {
  const resend = useResendInvite();

  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/40 bg-warning/10 p-4"
    >
      <div>
        <p className="font-medium">Запрошення не прийнято</p>
        <p className="text-sm text-slate">
          Пароль ще не задано, увійти неможливо. Посилання з листа діє 7 днів.
        </p>
      </div>
      {canResend && (
        <Button
          variant="outline"
          disabled={resend.isPending}
          onClick={() =>
            resend.mutate(userId, {
              onSuccess: () => toast.success(`Запрошення надіслано ще раз на ${email}`),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          {resend.isPending ? "Надсилаємо…" : "Надіслати запрошення ще раз"}
        </Button>
      )}
    </div>
  );
}
