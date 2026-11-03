"use client";

import { useActionState } from "react";

import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { exitChildMode } from "@/lib/actions/auth";
import { copy } from "@/lib/copy";

export function ExitForm() {
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
      <FormMessage message={state.message} />
      <SubmitButton size="lg">{copy.exitChildMode.submit}</SubmitButton>
    </form>
  );
}
