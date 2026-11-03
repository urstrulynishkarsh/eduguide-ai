"use client";

import { useState } from "react";

import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { removeChild } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

/** "Remove Aarav", then a second, explicit "Yes, remove": the deletion cannot be undone. */
export function RemoveChild({ studentId, name }: { studentId: string; name: string }) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <Button variant="outline" className="text-destructive" onClick={() => setConfirming(true)}>
        {copy.parent.remove(name)}
      </Button>
    );
  }
  return (
    <form action={removeChild.bind(null, studentId)} className="flex flex-wrap gap-2">
      <SubmitButton variant="destructive">{copy.parent.removeConfirm}</SubmitButton>
      <Button type="button" variant="ghost" onClick={() => setConfirming(false)}>
        {copy.parent.cancel}
      </Button>
    </form>
  );
}
