"use client";

import { useTransition } from "react";

import { useCopy } from "@/components/copy-provider";
import { chooseChild } from "@/lib/actions/books";
import { classLabel } from "@/lib/copy";
import type { Student } from "@/lib/types";

/** "Showing: Aarav ▾" — whose books, practice and progress the parent area shows. */
export function ChildSwitcher({ items, chosenId }: { items: Student[]; chosenId: string }) {
  const [pending, startTransition] = useTransition();
  const copy = useCopy();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{copy.switcher.label}</span>
      <select
        value={chosenId}
        disabled={pending}
        onChange={(event) => startTransition(() => chooseChild(event.target.value))}
        className="h-9 rounded-md border bg-card px-3 font-medium shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {items.map((child) => (
          <option key={child.id} value={child.id}>
            {child.name}
            {child.profile ? ` · ${classLabel(copy, child.profile)}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
