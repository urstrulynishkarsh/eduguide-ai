"use client";

import { useActionState } from "react";

import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import type { FormState } from "@/lib/forms";

/**
 * One button that runs a Server Action with ready-made fields (sent as the form): mostly a practice or
 * a test - a place with the class's usual settings, a recommendation, a task of the study plan - or
 * the analysis of a book's papers. Shows why if it can't be done.
 */
export function StartButton({
  action,
  fields,
  label,
  variant,
  className,
  children,
}: {
  action: (state: FormState, formData: FormData) => Promise<FormState>;
  fields: Record<string, string | number | null | undefined>;
  label: string;
  variant?: React.ComponentProps<typeof SubmitButton>["variant"];
  className?: string;
  children?: React.ReactNode;
}) {
  const [state, formAction] = useActionState(action, {});
  return (
    <form action={formAction} className="grid content-start gap-2">
      {Object.entries(fields).map(
        ([name, value]) => value != null && <input key={name} type="hidden" name={name} value={value} />,
      )}
      <SubmitButton variant={variant} className={className} aria-label={label}>
        {children ?? label}
      </SubmitButton>
      <FormMessage error={state} />
    </form>
  );
}
