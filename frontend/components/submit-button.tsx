"use client";

import { useFormStatus } from "react-dom";

import { Button } from "@/components/ui/button";

/** A form's submit button that is disabled while the form is being sent. */
export function SubmitButton(props: React.ComponentProps<typeof Button>) {
  const { pending } = useFormStatus();
  return <Button type="submit" disabled={pending} aria-disabled={pending} {...props} />;
}
