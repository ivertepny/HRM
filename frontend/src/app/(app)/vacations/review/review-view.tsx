"use client";

import { useState } from "react";

import { PageHeader } from "@/components/app/section";
import { cn } from "@/lib/utils";
import { canAnywhere } from "@/lib/access";
import { useMe, useMyAccess, useMyEmployee, useVacations } from "@/lib/queries";

import { ReviewQueue } from "./review-queue";
import { TeamCalendar } from "./team-calendar";

type Tab = "queue" | "calendar";

export function ReviewView() {
  const [tab, setTab] = useState<Tab>("queue");
  const me = useMe();
  const myEmployee = useMyEmployee(me.data?.id);
  const access = useMyAccess();
  const canManage = canAnywhere(access.data, "vacations:manage");
  const pending = useVacations({ status: "pending" }, canManage);
  const count = pending.data?.length;

  if (access.isSuccess && !canManage) {
    return (
      <div className="grid gap-4">
        <PageHeader title="Відпустки команди" />
        <p className="max-w-[60ch] text-slate">
          Розділ для тих, хто розглядає заявки (HR, керівники). Свої відпустки дивіться в
          розділі «Мої відпустки».
        </p>
      </div>
    );
  }

  const tabs: [Tab, string][] = [
    ["queue", count ? `На розгляді (${count})` : "На розгляді"],
    ["calendar", "Календар"],
  ];

  return (
    <div className="grid gap-8">
      <PageHeader title="Відпустки команди">
        Заявки працівників ваших підрозділів і хто коли відсутній.
      </PageHeader>

      <div role="tablist" aria-label="Подання" className="flex gap-1 border-b border-border">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            onClick={() => setTab(id)}
            className={cn(
              "-mb-px border-b-2 px-3 py-2 text-[0.9375rem] focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
              tab === id ? "border-primary font-medium" : "border-transparent text-slate hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "queue" ? (
          <ReviewQueue myEmployeeId={myEmployee.data?.id ?? undefined} />
        ) : (
          <TeamCalendar />
        )}
      </div>
    </div>
  );
}
