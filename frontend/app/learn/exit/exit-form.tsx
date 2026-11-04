"use client";

import { useActionState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { exitChildMode } from "@/lib/actions/auth";

export function ExitForm() {
  const copy = useCopy();
  const [state, formAction] = useActionState(exitChildMode, {});
  return (
    <form action={formAction} className="grid gap-4">
      <Field
        name="password"
        label={copy.exitChildMode.password}
        type="password"
        autoComplete="current-password"
        required
        error={state.fieldErrors?.password}
      />
      <FormMessage error={state} />
      <SubmitButton size="lg">{copy.exitChildMode.submit}</SubmitButton>
    </form>
  );
}
