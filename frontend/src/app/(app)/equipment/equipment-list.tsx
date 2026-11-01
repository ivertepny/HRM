"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { EquipmentStateTag } from "@/components/app/equipment-state";
import { NativeSelect } from "@/components/app/native-select";
import { PageHeader } from "@/components/app/section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import {
  CATEGORY_LABELS,
  STATE_LABELS,
  type EquipmentCategory,
  type EquipmentState,
} from "@/lib/equipment";
import { formatDate } from "@/lib/format";
import { useDebounced } from "@/lib/hooks";
import { useCreateEquipment, useEquipmentList, useMyAccess } from "@/lib/queries";

import { EquipmentForm } from "./equipment-form";

const PAGE_SIZE = 20;

export function EquipmentList() {
  const router = useRouter();
  const access = useMyAccess();
  const canManage = canAnywhere(access.data, "equipment:manage");
  const create = useCreateEquipment();

  const [search, setSearch] = useState("");
  const [state, setState] = useState<EquipmentState | "">("");
  const [category, setCategory] = useState<EquipmentCategory | "">("");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const term = useDebounced(search.trim());

  const list = useEquipmentList({
    page,
    page_size: PAGE_SIZE,
    search: term || undefined,
    state: state || undefined,
    category: category || undefined,
  });

  const reset =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value);
      setPage(1);
    };

  const count = list.data?.count ?? 0;
  const from = (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, count);
  const filtered = Boolean(term || state || category);

  return (
    <div className="grid gap-8">
      <PageHeader title="Обладнання">
        Облік техніки: що на складі, що в кого на руках, що списано.
      </PageHeader>

      {canManage &&
        (adding ? (
          <EquipmentForm
            submitLabel="Додати на склад"
            pendingLabel="Додаємо…"
            onCancel={() => setAdding(false)}
            onSubmit={async (values) => {
              const item = await create.mutateAsync(values);
              toast.success("Додано на склад");
              router.push(`/equipment/${item.id}`);
            }}
          />
        ) : (
          <div>
            <Button onClick={() => setAdding(true)}>Додати обладнання</Button>
          </div>
        ))}

      <div className="grid gap-4 border-t border-border pt-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-end">
        <div className="grid gap-2">
          <Label htmlFor="eq-search">Пошук</Label>
          <Input
            id="eq-search"
            type="search"
            placeholder="Назва або серійний номер"
            value={search}
            onChange={(e) => reset(setSearch)(e.target.value)}
            className="h-10"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="eq-state">Стан</Label>
          <NativeSelect
            id="eq-state"
            value={state}
            onChange={(e) => reset(setState)(e.target.value as EquipmentState | "")}
          >
            <option value="">Будь-який</option>
            {Object.entries(STATE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="eq-category-filter">Категорія</Label>
          <NativeSelect
            id="eq-category-filter"
            value={category}
            onChange={(e) => reset(setCategory)(e.target.value as EquipmentCategory | "")}
          >
            <option value="">Усі</option>
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>

      {list.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : list.isError ? (
        <p role="alert">Не вдалося завантажити обладнання: {list.error.message}</p>
      ) : count === 0 ? (
        <p className="text-slate">
          {filtered
            ? "Нічого не знайдено. Спробуйте інший запит або приберіть фільтри."
            : "Обладнання ще не внесено."}
        </p>
      ) : (
        <>
          <table className="w-full border-collapse text-left" aria-busy={list.isFetching}>
            <caption className="sr-only">Обладнання</caption>
            <thead className="text-sm text-slate">
              <tr className="hidden md:table-row">
                <th className="pb-3 font-normal">Назва</th>
                <th className="pb-3 font-normal">Категорія</th>
                <th className="pb-3 font-normal">Стан</th>
                <th className="pb-3 font-normal">У кого</th>
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((item) => (
                <tr
                  key={item.id}
                  className="grid gap-1 border-t border-border py-4 md:table-row md:py-0"
                >
                  <td className="md:py-3 md:pr-6">
                    <Link
                      href={`/equipment/${item.id}`}
                      className="rounded-sm font-medium hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                    >
                      {item.name}
                    </Link>
                    <span className="block font-mono text-sm text-slate">{item.serial_number}</span>
                  </td>
                  <td className="md:py-3 md:pr-6">{CATEGORY_LABELS[item.category ?? "other"]}</td>
                  <td className="md:py-3 md:pr-6">
                    <EquipmentStateTag state={item.state ?? "in_stock"} />
                  </td>
                  <td className="md:py-3">
                    {item.holder ? (
                      <>
                        {item.holder.name}
                        <span className="block text-sm text-slate">
                          з {formatDate(item.held_since)}
                        </span>
                      </>
                    ) : item.written_off_at ? (
                      <span className="text-slate">списано {formatDate(item.written_off_at)}</span>
                    ) : (
                      <span className="text-slate">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <nav aria-label="Сторінки" className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-slate">
              {from}–{to} з {count}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Попередня
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!list.data.next}
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
