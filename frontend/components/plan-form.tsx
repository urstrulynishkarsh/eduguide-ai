"use client";

import { useActionState, useState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Choice, ErrorText } from "@/components/choice";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { createPlan } from "@/lib/actions/plans";
import type { Chapter } from "@/lib/types";

/**
 * "Make a study plan": the exam date, minutes a day, the target and the chapters in the exam (none
 * chosen = all of them). The backend checks every rule and makes the tasks.
 */
export function PlanForm({
  area,
  studentId,
  books,
  replaces,
}: {
  area: "parent" | "learn";
  studentId?: string;
  books: { id: string; title: string; chapters: Chapter[] }[];
  /** The learner has a plan already. */
  replaces: boolean;
}) {
  const copy = useCopy();
  const text = copy.plans;
  const [state, formAction] = useActionState(createPlan.bind(null, area), {});
  const [chosen, setChosen] = useState<string[]>([]);
  const errors = state.fieldErrors ?? {};
  const toggle = (id: string) =>
    setChosen((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));

  return (
    <form action={formAction} className="grid gap-8">
      {studentId && <input type="hidden" name="student_id" value={studentId} />}
      <div className="flex flex-wrap gap-4 *:w-56">
        <Field name="exam_date" label={text.examDate} type="date" required error={errors.exam_date} />
        <Field
          name="daily_minutes"
          label={text.dailyMinutes}
          hint={text.dailyMinutesHint}
          type="number"
          min={10}
          max={300}
          defaultValue={30}
          required
          error={errors.daily_minutes}
        />
        <Field
          name="target_score"
          label={text.target}
          hint={text.targetHint}
          type="number"
          min={40}
          max={100}
          defaultValue={80}
          required
          error={errors.target_score}
        />
      </div>
      <fieldset className="grid gap-3">
        <legend className="mb-2 text-sm font-medium">{text.chapters}</legend>
        <p className="-mt-1 text-sm text-muted-foreground">{text.chaptersHint}</p>
        {books.map(
          (book) =>
            book.chapters.length > 0 && (
              <div key={book.id} className="grid gap-2">
                <p className="text-sm font-semibold">📘 {book.title}</p>
                <div className="flex flex-wrap gap-2">
                  {book.chapters.map((chapter) => (
                    <Choice
                      key={chapter.id}
                      type="checkbox"
                      name="chapter_ids"
                      value={chapter.id}
                      label={chapter.label}
                      checked={chosen.includes(chapter.id)}
                      onChange={() => toggle(chapter.id)}
                    />
                  ))}
                </div>
              </div>
            ),
        )}
        <ErrorText error={errors.chapter_ids} />
      </fieldset>
      {replaces && <p className="text-sm text-muted-foreground">{text.replaces}</p>}
      <FormMessage error={state} />
      <SubmitButton size="lg" className="justify-self-start">
        {text.submit}
      </SubmitButton>
    </form>
  );
}
