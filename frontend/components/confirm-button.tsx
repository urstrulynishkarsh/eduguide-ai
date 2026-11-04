"use client";

import { useState } from "react";

import { SubmitButton } from "@/components/submit-button";
import { useCopy } from "@/components/copy-provider";
import { Button } from "@/components/ui/button";

/** A button for something that cannot be undone: it asks a second, explicit time. */
export function ConfirmButton({
  label,
  confirmLabel,
  action,
}: {
  label: string;
  confirmLabel: string;
  action: () => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const copy = useCopy();
  if (!confirming) {
    return (
      <Button variant="outline" className="text-destructive" onClick={() => setConfirming(true)}>
        {label}
      </Button>
    );
  }
  return (
    <form action={action} className="flex flex-wrap gap-2">
      <SubmitButton variant="destructive">{confirmLabel}</SubmitButton>
      <Button type="button" variant="ghost" onClick={() => setConfirming(false)}>
        {copy.cancel}
      </Button>
    </form>
  );
}
