import { cn } from "@/lib/utils";

/** Нативний select у стилі полів: доступний з клавіатури й зручний на мобільних. */
export function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-md border border-input bg-transparent px-3 text-sm outline-none",
        "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
