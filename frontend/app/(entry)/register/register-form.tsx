"use client";

import { useActionState, useState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { register } from "@/lib/actions/auth";
import { cn } from "@/lib/utils";

/** "Who are you? Parent / Student" first (spec §10); the account fields appear once that is answered. */
export function RegisterForm() {
  const copy = useCopy();
  const text = copy.register;
  const roles = [
    { code: "parent", emoji: "👨‍👩‍👧", label: text.parent, hint: text.parentHint },
    { code: "student", emoji: "🎒", label: text.student, hint: text.studentHint },
  ];
  const [state, formAction] = useActionState(register, {});
  const [role, setRole] = useState(state.values?.role ?? "");

  return (
    <form action={formAction} className="grid gap-6">
      <fieldset className="grid gap-3">
        <legend className="mb-3 font-display text-xl font-bold">{text.whoAreYou}</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {roles.map((option) => (
            <label key={option.code} className="cursor-pointer">
              <input
                type="radio"
                name="role"
                value={option.code}
                checked={role === option.code}
                onChange={() => setRole(option.code)}
                className="peer sr-only"
              />
              <span
                className={cn(
                  "grid gap-1 rounded-xl border-2 bg-card p-5 transition-colors hover:border-primary/50",
                  "peer-checked:border-primary peer-checked:bg-secondary peer-focus-visible:ring-[3px] peer-focus-visible:ring-ring/50",
                )}
              >
                <span aria-hidden className="text-3xl">
                  {option.emoji}
                </span>
                <span className="font-display text-lg font-bold">{option.label}</span>
                <span className="text-sm text-muted-foreground">{option.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {role && (
        <div className="grid gap-4">
          <Field
            name="full_name"
            label={text.fullName}
            autoComplete="name"
            required
            maxLength={120}
            defaultValue={state.values?.full_name}
            error={state.fieldErrors?.full_name}
          />
          <Field
            name="email"
            label={text.email}
            type="email"
            autoComplete="email"
            required
            defaultValue={state.values?.email}
            error={state.fieldErrors?.email}
          />
          <Field
            name="password"
            label={text.password}
            hint={text.passwordHint}
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={128}
            error={state.fieldErrors?.password}
          />
          <FormMessage error={state} />
          <SubmitButton size="lg">{text.submit}</SubmitButton>
        </div>
      )}
    </form>
  );
}
