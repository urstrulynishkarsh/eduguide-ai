"use client";

import { useCopy } from "@/components/copy-provider";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { PinPad, usePinFormState } from "@/components/pin-pad";
import { SubmitButton } from "@/components/submit-button";
import type { PinState } from "@/lib/actions/auth";

interface PinFormProps {
  action: (state: PinState, formData: FormData) => Promise<PinState>;
  submitLabel: string;
}

/**
 * Sets or changes the parent PIN: the account's password, then the PIN twice on the number pad
 * (Settings, and before the first hand-over).
 */
export function PinForm({ action, submitLabel }: PinFormProps) {
  const text = useCopy().parentPin;
  const [state, formAction] = usePinFormState(action);
  return (
    <form action={formAction} className="grid gap-5">
      <Field
        name="password"
        label={text.password}
        type="password"
        autoComplete="current-password"
        required
        error={state.fieldErrors?.password}
      />
      <div key={state.answers} className="grid gap-6 sm:grid-cols-2">
        <PinPad name="pin" label={text.pin} error={state.fieldErrors?.pin} />
        <PinPad name="pin_again" label={text.again} />
      </div>
      <FormMessage error={state} />
      {state.saved && (
        <p role="status" className="rounded-md border border-accent bg-accent/20 px-3 py-2 text-sm">
          {text.saved}
        </p>
      )}
      <SubmitButton size="lg" className="justify-self-start">
        {submitLabel}
      </SubmitButton>
      <p className="text-sm text-muted-foreground">{text.tip}</p>
    </form>
  );
}
