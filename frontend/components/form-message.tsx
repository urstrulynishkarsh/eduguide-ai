"use client";

import { useCopy } from "@/components/copy-provider";
import { said } from "@/lib/copy";
import type { Refusal } from "@/lib/forms";

/**
 * Why something was refused (a form's state, a practice or a file that failed), read out by screen
 * readers as soon as it appears. Said by its code in the screen language where the words exist,
 * otherwise as the backend wrote it.
 */
export function FormMessage({ error, message }: { error?: Refusal | null; message?: string }) {
  const copy = useCopy();
  const text = message ?? (error ? said(copy.errors, error.code ?? "", error.message ?? "") : "");
  if (!text) return null;
  return (
    <p
      role="alert"
      className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
    >
      {text}
    </p>
  );
}
