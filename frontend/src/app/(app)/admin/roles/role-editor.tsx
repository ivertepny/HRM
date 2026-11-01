"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDeleteRole, useSaveRole } from "@/lib/admin-queries";
import type { ResourceRow } from "@/lib/admin";
import { ApiError, type Schemas } from "@/lib/api/client";
import { plural } from "@/lib/format";

import { PermissionMatrix } from "./permission-matrix";

type Role = Schemas["Role"];

export function RoleEditor({
  role,
  rows,
  canManage,
  onSaved,
  onDeleted,
}: {
  /** undefined — нова роль. */
  role?: Role;
  rows: ResourceRow[];
  canManage: boolean;
  onSaved: (role: Role) => void;
  onDeleted: () => void;
}) {
  const save = useSaveRole(role?.id);
  const remove = useDeleteRole();
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [granted, setGranted] = useState<string[]>(role?.permissions ?? []);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const editable = canManage;
  const original = role?.permissions ?? [];
  const dirty =
    name !== (role?.name ?? "") ||
    description !== (role?.description ?? "") ||
    granted.length !== original.length ||
    granted.some((p) => !original.includes(p));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    try {
      const saved = await save.mutateAsync({ name, description, permissions: granted });
      toast.success(role ? "Роль збережено" : "Роль створено");
      onSaved(saved);
    } catch (error) {
      if (error instanceof ApiError) setErrors(error.fieldErrors);
      toast.error((error as Error).message);
    }
  }

  async function destroy() {
    try {
      await remove.mutateAsync(role!.id!);
    } catch (error) {
      toast.error((error as Error).message);
      return;
    }
    toast.success(`Роль «${role!.name}» видалено`);
    onDeleted();
  }

  const holders = role?.users_count ?? 0;

  return (
    <form onSubmit={submit} className="grid gap-6">
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="grid gap-2">
          <Label htmlFor="role-name">Назва</Label>
          <Input
            id="role-name"
            value={name}
            required
            disabled={!editable || role?.is_system}
            onChange={(e) => setName(e.target.value)}
            className="h-10"
          />
          {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="role-description">Опис</Label>
          <Input
            id="role-description"
            value={description}
            disabled={!editable}
            onChange={(e) => setDescription(e.target.value)}
            className="h-10"
          />
        </div>
      </div>

      {role?.is_system && (
        <p className="text-sm text-slate">
          Системна роль: її не можна перейменувати чи видалити, але дозволи редагуються.
        </p>
      )}

      <PermissionMatrix rows={rows} granted={granted} editable={editable} onChange={setGranted} />
      {errors.permissions && (
        <p role="alert" className="text-sm text-destructive">
          {errors.permissions}
        </p>
      )}

      {editable && (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={!dirty || !name.trim() || save.isPending}>
            {role ? "Зберегти роль" : "Створити роль"}
          </Button>
          {role && !role.is_system && (
            <Button
              type="button"
              variant="ghost"
              disabled={holders > 0 || remove.isPending}
              title={holders > 0 ? "Спершу відкличте роль у всіх користувачів" : undefined}
              onClick={destroy}
            >
              Видалити роль
            </Button>
          )}
          {role && !role.is_system && holders > 0 && (
            <p className="self-center text-sm text-slate">
              Роль має {holders}{" "}
              {plural(holders, ["користувач", "користувачі", "користувачів"])} — видалити можна
              після відкликання.
            </p>
          )}
        </div>
      )}
    </form>
  );
}
