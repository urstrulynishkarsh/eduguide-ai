"use client";

import { useActionState } from "react";

import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { signIn } from "@/lib/actions/auth";
import { copy } from "@/lib/copy";

export function LoginForm() {
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
      <FormMessage message={state.message} />
      <SubmitButton size="lg">{copy.login.submit}</SubmitButton>
    </form>
  );
}
