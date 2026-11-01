"use client";

import Link from "next/link";
import { Suspense, useState } from "react";

import { SidebarNav, SidebarNavSkeleton } from "./sidebar-nav";
import { UserMenu } from "./user-menu";

/** Сірий «стіл» з навігацією зліва; вміст сторінки — білий аркуш. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15.5rem_minmax(0,1fr)]">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-sheet focus:px-3 focus:py-2"
      >
        Перейти до вмісту
      </a>

      <aside className="border-sidebar-border md:sticky md:top-0 md:h-dvh md:border-r md:py-7">
        <div className="flex items-center justify-between px-4 py-4 md:block md:px-3 md:py-0">
          <Link
            href="/"
            className="font-heading text-[1.375rem] font-semibold tracking-[-0.02em] md:px-3"
          >
            Кадри
          </Link>
          <div className="flex items-center gap-1 md:hidden">
            <UserMenu />
            <button
              type="button"
              className="rounded-md px-3 py-1.5 text-sm hover:bg-muted"
              aria-expanded={menuOpen}
              aria-controls="sidebar-nav"
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? "Закрити" : "Меню"}
            </button>
          </div>
        </div>
        <div
          id="sidebar-nav"
          className={`${menuOpen ? "block" : "hidden"} px-1 pb-6 md:mt-9 md:block md:px-1 md:pb-0`}
        >
          <Suspense fallback={<SidebarNavSkeleton />}>
            <SidebarNav onNavigate={() => setMenuOpen(false)} />
          </Suspense>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="hidden justify-end px-8 pt-5 md:flex">
          <UserMenu />
        </header>
        <main
          id="content"
          className="mx-3 mt-1 mb-6 flex-1 rounded-lg bg-sheet px-5 py-8 md:mx-8 md:mb-8 md:px-12 md:py-12"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
