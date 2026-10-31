"use client";

import Link from "next/link";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logout, useMe } from "@/lib/queries";

import { fullName, initials } from "./user-name";

export function UserMenu() {
  const { data: me } = useMe();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        aria-label="Меню користувача"
      >
        <span className="hidden text-sm sm:block">
          <span className="block font-medium">{fullName(me)}</span>
          <span className="block text-slate">{me?.email}</span>
        </span>
        <Avatar className="size-9">
          <AvatarFallback className="bg-ink text-sm text-mist">{initials(me)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-48">
        <DropdownMenuItem render={<Link href="/profile" />}>Мій профіль</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => logout()}>Вийти</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
