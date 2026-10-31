"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { activeHref, visibleNavigation } from "@/lib/navigation";
import { useMyAccess } from "@/lib/queries";

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { data: access, isPending } = useMyAccess();

  if (isPending) {
    return (
      <div className="grid gap-3 px-3" aria-busy="true" aria-label="Завантаження меню">
        {Array.from({ length: 5 }, (_, i) => (
          <Skeleton key={i} className="h-5 w-3/4 bg-sidebar-accent" />
        ))}
      </div>
    );
  }

  const current = activeHref(pathname);

  return (
    <nav aria-label="Розділи" className="grid gap-7">
      {visibleNavigation(access).map((group) => (
        <div key={group.label}>
          <p className="px-3 pb-2 text-[0.8125rem] text-slate">{group.label}</p>
          <ul className="grid gap-px">
            {group.items.map((item) => {
              const active = item.href === current;
              if (item.soon) {
                return (
                  <li key={item.href}>
                    <span
                      aria-disabled="true"
                      title="Розділ з'явиться в наступних версіях"
                      className="flex items-baseline justify-between gap-2 px-3 py-1.5 text-[0.9375rem] text-slate/70"
                    >
                      {item.label}
                      <span className="text-xs">незабаром</span>
                    </span>
                  </li>
                );
              }
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "block rounded-sm border-l-2 border-transparent px-3 py-1.5 text-[0.9375rem] transition-colors",
                      "hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                      active && "border-primary bg-sheet font-medium text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
