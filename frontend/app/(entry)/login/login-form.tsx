"use client";

import { useActionState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { signIn } from "@/lib/actions/auth";

export function LoginForm() {
  const copy = useCopy();
  const [state, formAction] = useActionState(signIn, {});
  return (
    <form action={formAction} className="grid gap-4">
      <Field
        name="email"
        label={copy.login.email}
        type="email"
        autoComplete="email"
        required
        defaultValue={state.values?.email}
        error={state.fieldErrors?.email}
      />
      <Field
        name="password"
        label={copy.login.password}
        type="password"
        autoComplete="current-password"
        required
        error={state.fieldErrors?.password}
      />
      <FormMessage error={state} />
      <SubmitButton size="lg">{copy.login.submit}</SubmitButton>
    </form>
  );
}
