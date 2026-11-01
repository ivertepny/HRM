"use client";

import Link from "next/link";
import { useState } from "react";

import { NativeSelect } from "@/components/app/native-select";
import { PageHeader } from "@/components/app/section";
import { fullName } from "@/components/app/user-name";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { useDebounced } from "@/lib/hooks";
import { useUsers } from "@/lib/admin-queries";
import { formatDate, plural } from "@/lib/format";
import { useMyAccess } from "@/lib/queries";

import { CreateUserForm } from "./create-user-form";

const PAGE_SIZE = 20;
const ACCOUNTS: [string, string, string] = ["обліковий запис", "облікові записи", "облікових записів"];

type Status = "active" | "inactive";
type Profile = "" | "yes" | "no";

export function UserList() {
  const access = useMyAccess();
  const canCreate = canAnywhere(access.data, "users:write");
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<Status | "">("");
  const [profile, setProfile] = useState<Profile>("");
  const [page, setPage] = useState(1);
  const term = useDebounced(search.trim());

  const users = useUsers({
    page,
    page_size: PAGE_SIZE,
    search: term || undefined,
    status: status || undefined,
    has_employee: profile === "" ? undefined : profile === "yes",
  });

  const reset =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value);
      setPage(1);
    };

  const count = users.data?.count ?? 0;

  return (
    <div className="grid gap-8">
      <PageHeader title="Облікові записи">
        {users.isSuccess && `${count} ${plural(count, ACCOUNTS)}.`}
      </PageHeader>

      {canCreate &&
        (creating ? (
          <CreateUserForm onCancel={() => setCreating(false)} />
        ) : (
          <div>
            <Button onClick={() => setCreating(true)}>Створити обліковий запис</Button>
          </div>
        ))}

      <div className="grid gap-4 border-t border-border pt-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-end">
        <div className="grid gap-2">
          <Label htmlFor="user-search">Пошук</Label>
          <Input
            id="user-search"
            type="search"
            placeholder="Ім'я або пошта"
            value={search}
            onChange={(e) => reset(setSearch)(e.target.value)}
            className="h-10"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="user-status">Статус</Label>
          <NativeSelect
            id="user-status"
            value={status}
            onChange={(e) => reset(setStatus)(e.target.value as Status | "")}
          >
            <option value="">Будь-який</option>
            <option value="active">Активні</option>
            <option value="inactive">Вимкнені</option>
          </NativeSelect>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="user-profile">Профіль працівника</Label>
          <NativeSelect
            id="user-profile"
            value={profile}
            onChange={(e) => reset(setProfile)(e.target.value as Profile)}
          >
            <option value="">Неважливо</option>
            <option value="yes">Оформлений</option>
            <option value="no">Ще не оформлений</option>
          </NativeSelect>
        </div>
      </div>

      {users.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : users.isError ? (
        <p role="alert">Не вдалося завантажити облікові записи: {users.error.message}</p>
      ) : count === 0 ? (
        <p className="text-slate">Нікого не знайдено. Змініть запит або фільтри.</p>
      ) : (
        <>
          <table className="w-full border-collapse text-left" aria-busy={users.isFetching}>
            <caption className="sr-only">Облікові записи</caption>
            <thead className="text-sm text-slate">
              <tr className="hidden md:table-row">
                <th className="pb-3 font-normal">Користувач</th>
                <th className="pb-3 font-normal">Статус</th>
                <th className="pb-3 font-normal">Профіль працівника</th>
                <th className="pb-3 font-normal">Останній вхід</th>
              </tr>
            </thead>
            <tbody>
              {users.data.results.map((user) => (
                <tr
                  key={user.id}
                  className="grid gap-1 border-t border-border py-4 md:table-row md:py-0"
                >
                  <td className="md:py-3 md:pr-6">
                    <Link
                      href={`/admin/users/${user.id}`}
                      className="font-medium hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                    >
                      {fullName(user)}
                    </Link>
                    <span className="block text-sm text-slate">{user.email}</span>
                  </td>
                  <td className="md:py-3 md:pr-6">
                    {user.status === "inactive" ? (
                      <span className="text-destructive">Вимкнений</span>
                    ) : (
                      "Активний"
                    )}
                  </td>
                  <td className="md:py-3 md:pr-6">
                    {user.employee ? "Оформлений" : <span className="text-slate">Немає</span>}
                  </td>
                  <td className="text-slate md:py-3">
                    {user.last_login ? formatDate(user.last_login) : "ще не входив(-ла)"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <nav aria-label="Сторінки" className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-slate">
              {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, count)} з {count}
            </span>
            <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              Попередня
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!users.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Наступна
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
