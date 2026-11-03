"use client";

import { useActionState } from "react";

import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { createPractice } from "@/lib/actions/practice";

/**
 * One button that starts practice with the class's usual settings for a place (a chapter, an
 * exercise, or everything when none is given). Shows why if the practice can't be made.
 */
export function QuickPractice({
  area,
  studentId,
  chapterId,
  exerciseId,
  label,
  className,
  children,
}: {
  area: "parent" | "learn";
  studentId?: string;
  chapterId?: string;
  exerciseId?: string;
  label: string;
  className?: string;
  children?: React.ReactNode;
}) {
  const [state, formAction] = useActionState(createPractice.bind(null, area), {});
  return (
    <form action={formAction} className="grid content-start gap-2">
      {studentId && <input type="hidden" name="student_id" value={studentId} />}
      {chapterId && <input type="hidden" name="chapter_id" value={chapterId} />}
      {exerciseId && <input type="hidden" name="exercise_id" value={exerciseId} />}
      <SubmitButton className={className} aria-label={label}>
        {children ?? label}
      </SubmitButton>
      <FormMessage message={state.message} />
    </form>
  );
}
