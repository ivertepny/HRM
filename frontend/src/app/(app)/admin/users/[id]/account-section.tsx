"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDeleteUser, useUpdateUser } from "@/lib/admin-queries";
import { ApiError, type Schemas } from "@/lib/api/client";

type User = Schemas["User"];

export function AccountSection({
  user,
  isSelf,
  canWrite,
  canDelete,
}: {
  user: User;
  isSelf: boolean;
  canWrite: boolean;
  canDelete: boolean;
}) {
  const router = useRouter();
  const update = useUpdateUser(user.id!);
  const remove = useDeleteUser();
  const [values, setValues] = useState({
    first_name: user.first_name ?? "",
    last_name: user.last_name ?? "",
    email: user.email ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirmDelete, setConfirmDelete] = useState(false);
  const dirty =
    values.first_name !== (user.first_name ?? "") ||
    values.last_name !== (user.last_name ?? "") ||
    values.email !== user.email;
  const inactive = user.status === "inactive";

  const onError = (error: Error) => {
    if (error instanceof ApiError) setErrors(error.fieldErrors);
    toast.error(error.message);
  };

  function save(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    update.mutate(values, { onSuccess: () => toast.success("Зміни збережено"), onError });
  }

  function setStatus(status: "active" | "inactive") {
    update.mutate(
      { status },
      {
        onSuccess: () =>
          toast.success(status === "active" ? "Обліковий запис увімкнено" : "Обліковий запис вимкнено"),
        onError,
      },
    );
  }

  async function destroy() {
    try {
      await remove.mutateAsync(user.id!);
    } catch (error) {
      toast.error((error as Error).message);
      return;
    }
    toast.success("Обліковий запис видалено");
    router.push("/admin/users");
  }

  return (
    <div className="grid gap-6">
      <form onSubmit={save} className="grid max-w-xl gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["first_name", "Ім'я"],
              ["last_name", "Прізвище"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="grid gap-2">
              <Label htmlFor={`acc-${key}`}>{label}</Label>
              <Input
                id={`acc-${key}`}
                value={values[key]}
                disabled={!canWrite}
                onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))}
                className="h-10"
              />
              {errors[key] && <p className="text-sm text-destructive">{errors[key]}</p>}
            </div>
          ))}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="acc-email">Пошта для входу</Label>
          <Input
            id="acc-email"
            type="email"
            value={values.email}
            disabled={!canWrite}
            onChange={(e) => setValues((v) => ({ ...v, email: e.target.value }))}
            className="h-10"
          />
          {errors.email && <p className="text-sm text-destructive">{errors.email}</p>}
        </div>
        {canWrite && (
          <div>
            <Button type="submit" disabled={!dirty || update.isPending}>
              Зберегти зміни
            </Button>
          </div>
        )}
      </form>

      <div className="grid max-w-xl gap-3 rounded-md bg-mist p-4">
        <p>
          {inactive ? (
            <>
              <span className="font-medium text-destructive">Вимкнений.</span> Увійти не може;
              активні сесії вже завершено.
            </>
          ) : (
            <>
              <span className="font-medium">Активний.</span> Може входити в систему.
            </>
          )}
        </p>
        {errors.status && <p className="text-sm text-destructive">{errors.status}</p>}
        {canWrite && !isSelf && (
          <div>
            <Button
              variant={inactive ? "default" : "outline"}
              disabled={update.isPending}
              onClick={() => setStatus(inactive ? "active" : "inactive")}
            >
              {inactive ? "Увімкнути обліковий запис" : "Вимкнути обліковий запис"}
            </Button>
          </div>
        )}
        {isSelf && <p className="text-sm text-slate">Свій обліковий запис вимкнути не можна.</p>}
      </div>

      {canDelete && !isSelf && (
        <div className="grid max-w-xl gap-3">
          {confirmDelete ? (
            <div className="grid gap-3 rounded-md border border-destructive/30 p-4">
              <p>
                Видалення незворотне. Якщо людина вже працює в компанії, видалити не вийде —
                вимкніть обліковий запис замість цього.
              </p>
              <span className="flex gap-2">
                <Button variant="destructive" disabled={remove.isPending} onClick={destroy}>
                  Видалити обліковий запис
                </Button>
                <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
                  Не видаляти
                </Button>
              </span>
            </div>
          ) : (
            <div>
              <Button variant="ghost" onClick={() => setConfirmDelete(true)}>
                Видалити обліковий запис
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
