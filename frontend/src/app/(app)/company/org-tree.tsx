"use client";

import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import type { UnitNode } from "@/lib/org";

type TreeProps = {
  selectedId?: number;
  expanded: Set<number>;
  onToggle: (id: number) => void;
  onSelect: (id: number) => void;
};

/** Дерево підрозділів: вкладені списки з напрямними лініями, як у файловому дереві. */
export function OrgTree({ nodes, ...props }: TreeProps & { nodes: UnitNode[] }) {
  return (
    <ul className="grid gap-px text-[0.9375rem]" aria-label="Підрозділи">
      {nodes.map((node) => (
        <TreeNode key={node.id} node={node} {...props} />
      ))}
    </ul>
  );
}

function TreeNode({ node, ...props }: TreeProps & { node: UnitNode }) {
  const { selectedId, expanded, onToggle, onSelect } = props;
  const hasChildren = node.children.length > 0;
  const open = expanded.has(node.id!);
  const selected = node.id === selectedId;

  return (
    <li>
      <div
        className={cn(
          "flex items-center gap-1 rounded-sm pr-2",
          selected ? "bg-ink text-mist" : "hover:bg-mist",
        )}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggle(node.id!)}
            aria-expanded={open}
            aria-label={open ? `Згорнути «${node.name}»` : `Розгорнути «${node.name}»`}
            className="grid size-7 shrink-0 place-items-center rounded-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <ChevronRight
              aria-hidden
              className={cn("size-4 transition-transform", open && "rotate-90")}
            />
          </button>
        ) : (
          <span className="size-7 shrink-0" aria-hidden />
        )}
        <button
          type="button"
          onClick={() => onSelect(node.id!)}
          aria-current={selected ? "true" : undefined}
          className="flex min-w-0 flex-1 items-baseline justify-between gap-3 py-1.5 text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <span className="truncate">
            {node.name}
            {node.custom_type && (
              <span className={cn("ml-2 text-xs", selected ? "text-mist/70" : "text-slate")}>
                {node.custom_type}
              </span>
            )}
          </span>
          {!!node.employees_count && (
            <span
              className={cn("text-xs tabular-nums", selected ? "text-mist/80" : "text-slate")}
              title="Працівників безпосередньо в підрозділі"
            >
              {node.employees_count}
            </span>
          )}
        </button>
      </div>
      {hasChildren && open && (
        <ul className="ml-3.5 grid gap-px border-l border-border pl-2">
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} {...props} />
          ))}
        </ul>
      )}
    </li>
  );
}
