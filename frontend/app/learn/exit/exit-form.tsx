"use client";

import { useRef } from "react";

import { useCopy } from "@/components/copy-provider";
import { FormMessage } from "@/components/form-message";
import { PinPad, usePinFormState } from "@/components/pin-pad";
import { leaveChildMode } from "@/lib/actions/auth";

/** The parent PIN on the number pad; sent as soon as its last digit is in. */
export function ExitForm() {
  const copy = useCopy();
  const [state, formAction] = usePinFormState(leaveChildMode);
  const form = useRef<HTMLFormElement>(null);
  return (
    <form ref={form} action={formAction} className="grid justify-items-center gap-4">
      <PinPad
        key={state.answers}
        name="pin"
        label={copy.exitChildMode.pin}
        onComplete={() => form.current?.requestSubmit()}
      />
      <FormMessage error={state} />
    </form>
  );
}
