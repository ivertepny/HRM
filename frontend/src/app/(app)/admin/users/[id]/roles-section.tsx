"use client";

import { useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useGrantRole, useRevokeRole, useRoles, useUserRoles } from "@/lib/admin-queries";
import { unitPath } from "@/lib/employees";
import { formatDate } from "@/lib/format";
import { useUnits } from "@/lib/queries";

export function RolesSection({
  userId,
  canManage,
  canPickUnit,
}: {
  userId: number;
  canManage: boolean;
  canPickUnit: boolean;
}) {
  const assignments = useUserRoles(userId);
  const revoke = useRevokeRole();
  const [granting, setGranting] = useState(false);

  if (assignments.isPending) return <Skeleton className="h-20 w-full" />;
  if (assignments.isError) {
    return <p role="alert">Не вдалося завантажити ролі: {assignments.error.message}</p>;
  }

  async function revokeRole(id: number, name?: string) {
    try {
      await revoke.mutateAsync(id);
      toast.success(`Роль «${name}» відкликано`);
    } catch (error) {
      toast.error((error as Error).message);
    }
  }

  return (
    <div className="grid gap-5">
      {assignments.data.length === 0 ? (
        <p className="text-slate">Ролей немає — людина бачить лише власні дані.</p>
      ) : (
        <ul className="grid gap-3">
          {assignments.data.map((a) => (
            <li key={a.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span>
                <span className="font-medium">{a.role_name}</span>
                <span className="text-slate">
                  {" — "}
                  {a.structural_unit_name
                    ? `у підрозділі «${a.structural_unit_name}» і дочірніх`
                    : "уся компанія"}
                  {a.expires_at && `, до ${formatDate(a.expires_at)}`}
                </span>
                <span className="block text-xs text-slate">
                  Видав(-ла) {a.granted_by ?? "система"} {formatDate(a.granted_at)}
                </span>
              </span>
              {canManage && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={revoke.isPending}
                  onClick={() => revokeRole(a.id!, a.role_name)}
                >
                  Відкликати роль
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canManage &&
        (granting ? (
          <GrantForm userId={userId} canPickUnit={canPickUnit} onDone={() => setGranting(false)} />
        ) : (
          <div>
            <Button variant="outline" onClick={() => setGranting(true)}>
              Видати роль
            </Button>
          </div>
        ))}
    </div>
  );
}

function GrantForm({
  userId,
  canPickUnit,
  onDone,
}: {
  userId: number;
  canPickUnit: boolean;
  onDone: () => void;
}) {
  const roles = useRoles();
  const units = useUnits(canPickUnit);
  const grant = useGrantRole();
  const [role, setRole] = useState("");
  const [unit, setUnit] = useState("");
  const [expires, setExpires] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!role) {
      setError("Оберіть роль.");
      return;
    }
    grant.mutate(
      {
        user: userId,
        role: Number(role),
        structural_unit: unit ? Number(unit) : null,
        // Кінець обраного дня за місцевим часом
        expires_at: expires ? new Date(`${expires}T23:59:59`).toISOString() : null,
      },
      {
        onSuccess: () => {
          toast.success("Роль видано");
          onDone();
        },
        onError: (err) => setError(err.message),
      },
    );
  }

  return (
    <form onSubmit={submit} className="grid max-w-xl gap-4 rounded-md bg-mist p-4">
      <div className="grid gap-2">
        <Label htmlFor="grant-role">Роль</Label>
        <NativeSelect id="grant-role" value={role} onChange={(e) => setRole(e.target.value)} className="bg-sheet">
          <option value="">Оберіть роль</option>
          {(roles.data ?? []).map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="grid gap-2">
          <Label htmlFor="grant-unit">Діє</Label>
          <NativeSelect
            id="grant-unit"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="bg-sheet"
          >
            <option value="">У всій компанії</option>
            {(units.data ?? []).map((u) => (
              <option key={u.id} value={u.id}>
                У підрозділі {unitPath(u)}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="grant-expires">До (необов&apos;язково)</Label>
          <Input
            id="grant-expires"
            type="date"
            value={expires}
            onChange={(e) => setExpires(e.target.value)}
            className="h-10 bg-sheet"
          />
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <span className="flex gap-2">
        <Button type="submit" disabled={grant.isPending}>
          Видати роль
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}
