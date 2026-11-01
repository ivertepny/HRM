"use client";

import { cn } from "@/lib/utils";
import {
  ACTION_LABELS,
  ACTION_ORDER,
  cellState,
  FULL_ACCESS,
  toggle,
  type ResourceRow,
} from "@/lib/admin";

type Props = {
  rows: ResourceRow[];
  granted: string[];
  editable: boolean;
  onChange: (next: string[]) => void;
};

/** Ресурси × дії. Дозволи, які дає wildcard, показані, але окремо не знімаються. */
export function PermissionMatrix({ rows, granted, editable, onChange }: Props) {
  const full = granted.includes(FULL_ACCESS);

  return (
    <div className="grid gap-4">
      <label className="flex items-center gap-3">
        <input
          type="checkbox"
          className="size-4 accent-primary"
          checked={full}
          disabled={!editable}
          onChange={() => onChange(toggle(granted, FULL_ACCESS))}
        />
        <span>
          <span className="font-medium">Повний доступ до системи</span>
          <span className="block text-sm text-slate">Усі розділи й дії, зокрема майбутні.</span>
        </span>
      </label>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <caption className="sr-only">Дозволи ролі за розділами</caption>
          <thead className="text-slate">
            <tr>
              <th className="py-2 pr-4 font-normal">Розділ</th>
              {ACTION_ORDER.map((action) => (
                <th key={action} className="px-2 py-2 text-center font-normal">
                  {ACTION_LABELS[action]}
                </th>
              ))}
              <th className="px-2 py-2 text-center font-normal">Усі дії</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const all = `${row.resource}:*`;
              const allState = cellState(granted, all);
              return (
                <tr key={row.resource} className="border-t border-border">
                  <th scope="row" className="py-2.5 pr-4 font-medium">
                    {row.label}
                  </th>
                  {ACTION_ORDER.map((action) => {
                    if (!row.actions.includes(action)) {
                      return <td key={action} aria-hidden />;
                    }
                    const codename = `${row.resource}:${action}`;
                    const state = cellState(granted, codename);
                    return (
                      <td key={action} className="px-2 text-center">
                        <input
                          type="checkbox"
                          aria-label={`${row.label}: ${ACTION_LABELS[action]}`}
                          title={state === "implied" ? "Входить в «Усі дії» або повний доступ" : undefined}
                          className={cn("size-4 accent-primary", state === "implied" && "opacity-50")}
                          checked={state !== "off"}
                          disabled={!editable || state === "implied"}
                          onChange={() => onChange(toggle(granted, codename))}
                        />
                      </td>
                    );
                  })}
                  <td className="px-2 text-center">
                    <input
                      type="checkbox"
                      aria-label={`${row.label}: усі дії`}
                      className={cn("size-4 accent-primary", allState === "implied" && "opacity-50")}
                      checked={allState !== "off"}
                      disabled={!editable || allState === "implied"}
                      onChange={() => onChange(toggle(granted, all))}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
