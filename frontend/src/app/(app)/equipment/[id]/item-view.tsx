"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { EquipmentStateTag } from "@/components/app/equipment-state";
import { NativeSelect } from "@/components/app/native-select";
import { PageHeader, Section } from "@/components/app/section";
import { fullName } from "@/components/app/user-name";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { canAnywhere } from "@/lib/access";
import { ApiError } from "@/lib/api/client";
import {
  assignmentPeriod,
  availableActions,
  CATEGORY_LABELS,
  type Equipment,
  type EquipmentAction,
} from "@/lib/equipment";
import { formatDate } from "@/lib/format";
import { useDebounced } from "@/lib/hooks";
import {
  useAssignments,
  useDeleteEquipment,
  useEmployees,
  useEquipmentItem,
  useEquipmentOperation,
  useMyAccess,
  useUpdateEquipment,
} from "@/lib/queries";
import { todayISO } from "@/lib/vacations";

import { EquipmentForm } from "../equipment-form";

/** Помилка біля поля (дата, працівник) важливіша за загальне «Перевірте дані». */
function errorText(error: unknown) {
  if (error instanceof ApiError) {
    const [first] = Object.values(error.fieldErrors);
    if (first) return first;
  }
  return error instanceof Error ? error.message : String(error);
}

const ACTION_LABELS: Record<EquipmentAction, string> = {
  assign: "Видати працівнику",
  return: "Повернути на склад",
  edit: "Редагувати",
  "write-off": "Списати",
  delete: "Видалити",
};

export function ItemView() {
  const { id } = useParams<{ id: string }>();
  const itemId = Number(id);
  const item = useEquipmentItem(itemId);
  const history = useAssignments({ equipment: itemId });
  const access = useMyAccess();
  const [open, setOpen] = useState<EquipmentAction | null>(null);

  if (item.isPending) {
    return (
      <div className="grid gap-6" aria-busy="true">
        <Skeleton className="h-12 w-80" />
        <Skeleton className="h-40 w-full max-w-2xl" />
      </div>
    );
  }
  if (item.isError) {
    const notFound = item.error instanceof ApiError && item.error.status === 404;
    return (
      <div className="grid gap-4">
        <PageHeader title={notFound ? "Обладнання не знайдено" : "Не вдалося завантажити"} />
        <p className="text-slate">
          {notFound ? "Його немає або воно поза вашою областю доступу." : item.error.message}{" "}
          <Link href="/equipment" className="text-primary underline-offset-4 hover:underline">
            До списку обладнання
          </Link>
        </p>
      </div>
    );
  }

  const data = item.data;
  const can = (codename: string) => canAnywhere(access.data, codename);
  const actions = can("equipment:manage")
    ? availableActions(data, (history.data?.length ?? 1) > 0)
    : [];
  const close = () => setOpen(null);

  return (
    <div className="grid gap-10">
      <PageHeader title={data.name}>
        {CATEGORY_LABELS[data.category ?? "other"]} ·{" "}
        <span className="font-mono">{data.serial_number}</span>
      </PageHeader>

      <Section title="Стан">
        <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-[10rem_minmax(0,1fr)]">
          <dt className="text-slate">Стан</dt>
          <dd>
            <EquipmentStateTag state={data.state ?? "in_stock"} />
          </dd>
          {data.holder && (
            <>
              <dt className="text-slate">У кого</dt>
              <dd>
                {can("employees:read") ? (
                  <Link
                    href={`/employees/${data.holder.id}`}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    {data.holder.name}
                  </Link>
                ) : (
                  data.holder.name
                )}
                <span className="text-slate">, з {formatDate(data.held_since)}</span>
              </dd>
            </>
          )}
          {data.written_off_at && (
            <>
              <dt className="text-slate">Списано</dt>
              <dd>{formatDate(data.written_off_at)}</dd>
            </>
          )}
          {data.description && (
            <>
              <dt className="text-slate">Опис</dt>
              <dd className="whitespace-pre-line">{data.description}</dd>
            </>
          )}
        </dl>
      </Section>

      {actions.length > 0 && (
        <Section title="Дії">
          {open === null ? (
            <span className="flex flex-wrap gap-2">
              {actions.map((action, index) => (
                <Button
                  key={action}
                  variant={index === 0 ? "default" : "outline"}
                  onClick={() => setOpen(action)}
                >
                  {ACTION_LABELS[action]}
                </Button>
              ))}
            </span>
          ) : (
            <ActionPanel action={open} item={data} onDone={close} />
          )}
        </Section>
      )}

      <Section title="Історія видач" wide>
        {history.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : history.isError ? (
          <p role="alert">Не вдалося завантажити історію: {history.error.message}</p>
        ) : history.data.length === 0 ? (
          <p className="text-slate">Ще нікому не видавалось.</p>
        ) : (
          <ol className="grid gap-4">
            {history.data.map((entry) => (
              <li key={entry.id} className="grid gap-1 border-l-2 border-border pl-4">
                <span className="font-medium">{entry.employee?.name}</span>
                <span className="text-sm text-slate">
                  {assignmentPeriod(entry, formatDate)}
                  {entry.is_active && " · зараз у працівника"}
                </span>
                {entry.note && <span className="text-sm whitespace-pre-line">{entry.note}</span>}
              </li>
            ))}
          </ol>
        )}
      </Section>
    </div>
  );
}

function ActionPanel({
  action,
  item,
  onDone,
}: {
  action: EquipmentAction;
  item: Equipment;
  onDone: () => void;
}) {
  switch (action) {
    case "assign":
      return <AssignForm item={item} onDone={onDone} />;
    case "return":
      return <ReturnForm item={item} onDone={onDone} />;
    case "write-off":
      return <WriteOffForm item={item} onDone={onDone} />;
    case "edit":
      return <EditForm item={item} onDone={onDone} />;
    case "delete":
      return <DeleteConfirm item={item} onDone={onDone} />;
  }
}

function DateField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="date"
        required
        max={todayISO()}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 bg-sheet"
      />
    </div>
  );
}

function NoteField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="grid gap-2">
      <Label htmlFor="eq-note">Примітка</Label>
      <Input
        id="eq-note"
        maxLength={500}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Комплектація, стан при видачі чи поверненні"
        className="h-10 bg-sheet"
      />
    </div>
  );
}

function Panel({
  onSubmit,
  error,
  children,
  submit,
  onCancel,
}: {
  onSubmit: () => void;
  error: string | null;
  children: React.ReactNode;
  submit: React.ReactNode;
  onCancel: () => void;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      className="grid max-w-2xl gap-4 rounded-md bg-mist p-4"
    >
      {children}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <span className="flex gap-2">
        {submit}
        <Button type="button" variant="ghost" onClick={onCancel}>
          Скасувати
        </Button>
      </span>
    </form>
  );
}

function AssignForm({ item, onDone }: { item: Equipment; onDone: () => void }) {
  const operation = useEquipmentOperation(item.id!);
  const [search, setSearch] = useState("");
  const term = useDebounced(search.trim());
  const employees = useEmployees({
    active: true,
    page_size: 50,
    search: term || undefined,
  });
  const [employeeId, setEmployeeId] = useState("");
  const [date, setDate] = useState(todayISO());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const options = employees.data?.results ?? [];

  return (
    <Panel
      error={error}
      onCancel={onDone}
      onSubmit={() => {
        setError(null);
        operation.mutate(
          {
            action: "assign",
            body: { employee_id: Number(employeeId), date, note },
          },
          {
            onSuccess: (updated) => {
              toast.success(`Видано: ${updated.holder?.name}`);
              onDone();
            },
            onError: (e) => setError(errorText(e)),
          },
        );
      }}
      submit={
        <Button type="submit" disabled={!employeeId || operation.isPending}>
          {operation.isPending ? "Видаємо…" : "Видати"}
        </Button>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="eq-employee-search">Знайти працівника</Label>
          <Input
            id="eq-employee-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ім'я або пошта"
            className="h-10 bg-sheet"
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="eq-employee">Працівник</Label>
          <NativeSelect
            id="eq-employee"
            required
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            className="bg-sheet"
          >
            <option value="">
              {employees.isPending
                ? "Завантаження…"
                : options.length
                  ? "Оберіть працівника"
                  : "Нікого не знайдено"}
            </option>
            {options.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {fullName(employee.user)} — {employee.structural_unit?.full_name}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <DateField id="eq-date" label="Дата видачі" value={date} onChange={setDate} />
        <NoteField value={note} onChange={setNote} />
      </div>
    </Panel>
  );
}

function ReturnForm({ item, onDone }: { item: Equipment; onDone: () => void }) {
  const operation = useEquipmentOperation(item.id!);
  const [date, setDate] = useState(todayISO());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <Panel
      error={error}
      onCancel={onDone}
      onSubmit={() => {
        setError(null);
        operation.mutate(
          { action: "return", body: { date, note } },
          {
            onSuccess: () => {
              toast.success("Повернено на склад");
              onDone();
            },
            onError: (e) => setError(errorText(e)),
          },
        );
      }}
      submit={
        <Button type="submit" disabled={operation.isPending}>
          {operation.isPending ? "Повертаємо…" : "Підтвердити повернення"}
        </Button>
      }
    >
      <p className="text-sm">
        {item.holder?.name} повертає «{item.name}» на склад.
      </p>
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <DateField id="eq-date" label="Дата повернення" value={date} onChange={setDate} />
        <NoteField value={note} onChange={setNote} />
      </div>
    </Panel>
  );
}

function WriteOffForm({ item, onDone }: { item: Equipment; onDone: () => void }) {
  const operation = useEquipmentOperation(item.id!);
  const [date, setDate] = useState(todayISO());
  const [error, setError] = useState<string | null>(null);

  return (
    <Panel
      error={error}
      onCancel={onDone}
      onSubmit={() => {
        setError(null);
        operation.mutate(
          { action: "write-off", body: { date } },
          {
            onSuccess: () => {
              toast.success("Списано");
              onDone();
            },
            onError: (e) => setError(errorText(e)),
          },
        );
      }}
      submit={
        <Button type="submit" variant="destructive" disabled={operation.isPending}>
          {operation.isPending ? "Списуємо…" : "Списати"}
        </Button>
      }
    >
      <p className="text-sm">
        Списане обладнання лишається в обліку з історією, але більше не видається. Скасувати
        списання не можна.
      </p>
      <div className="max-w-56">
        <DateField id="eq-date" label="Дата списання" value={date} onChange={setDate} />
      </div>
    </Panel>
  );
}

function EditForm({ item, onDone }: { item: Equipment; onDone: () => void }) {
  const update = useUpdateEquipment(item.id!);
  return (
    <EquipmentForm
      initial={item}
      submitLabel="Зберегти"
      pendingLabel="Зберігаємо…"
      onCancel={onDone}
      onSubmit={async (values) => {
        await update.mutateAsync(values);
        toast.success("Збережено");
        onDone();
      }}
    />
  );
}

function DeleteConfirm({ item, onDone }: { item: Equipment; onDone: () => void }) {
  const router = useRouter();
  const remove = useDeleteEquipment();
  const [error, setError] = useState<string | null>(null);

  return (
    <Panel
      error={error}
      onCancel={onDone}
      onSubmit={() => {
        setError(null);
        remove.mutate(item.id!, {
          onSuccess: () => {
            toast.success("Видалено");
            router.push("/equipment");
          },
          onError: (e) => setError(errorText(e)),
        });
      }}
      submit={
        <Button type="submit" variant="destructive" disabled={remove.isPending}>
          {remove.isPending ? "Видаляємо…" : "Видалити назавжди"}
        </Button>
      }
    >
      <p className="text-sm">
        Видалення — для помилково внесених записів. Обладнання, яке вже видавали, видалити не можна:
        його списують.
      </p>
    </Panel>
  );
}
