"use client";

import { useActionState, useState } from "react";

import { Choice, ChoiceGroup, SelectField } from "@/components/choice";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { createPractice } from "@/lib/actions/practice";
import { createTest } from "@/lib/actions/tests";
import { copy } from "@/lib/copy";
import type { ClassProfile, Option, TestKind } from "@/lib/types";

const text = copy.practiceForm;

/**
 * The settings for a chosen place (spec §18): how many questions, how hard, the question type of a
 * practice or the time limit of a test (only where the class has timed tests), and the language.
 * Limits come from the class.
 */
export function QuestionSettingsForm({
  area,
  place,
  test,
  classProfile,
  languages,
  defaultLanguage,
}: {
  area: "parent" | "learn";
  place: Record<"student_id" | "book_id" | "chapter_id" | "exercise_id", string | undefined>;
  /** Make a test of this kind instead of a practice. */
  test?: TestKind;
  classProfile: ClassProfile;
  languages: Option[];
  defaultLanguage: string;
}) {
  const [state, formAction] = useActionState((test ? createTest : createPractice).bind(null, area), {});
  const [difficulty, setDifficulty] = useState("mixed");
  const [type, setType] = useState("mixed");
  const [language, setLanguage] = useState(defaultLanguage);
  const errors = state.fieldErrors ?? {};
  const max = classProfile.max_session_questions;
  const needsChapter = test === "chapter" && !place.chapter_id;

  return (
    <form action={formAction} className="grid gap-6">
      {Object.entries({ ...place, kind: test }).map(
        ([name, value]) => value && <input key={name} type="hidden" name={name} value={value} />,
      )}
      <div className="flex flex-wrap gap-4 *:w-56">
        <Field
          name="count"
          label={text.count}
          // A test left empty gets the usual length of its kind.
          hint={test ? copy.tests.countHint(max) : text.countHint(max)}
          type="number"
          min={1}
          max={max}
          defaultValue={test ? undefined : classProfile.default_session_questions}
          error={errors.count}
        />

        {test && classProfile.features.timed_tests && (
          <Field
            name="duration_minutes"
            label={copy.tests.timeLimit}
            hint={test === "full_mock" ? copy.tests.fullMockTimeHint : copy.tests.noTimeLimitHint}
            type="number"
            min={5}
            max={240}
            error={errors.duration_minutes}
          />
        )}
      </div>
      <ChoiceGroup legend={text.difficulty} error={errors.difficulty}>
        {["easy", "medium", "hard", "mixed"].map((code) => (
          <Choice
            key={code}
            name="difficulty"
            value={code}
            label={copy.difficulties[code]}
            checked={difficulty === code}
            onChange={() => setDifficulty(code)}
          />
        ))}
      </ChoiceGroup>
      <div className="grid gap-4 sm:grid-cols-2">
        {!test && (
          <SelectField
            name="question_type"
            label={text.type}
            value={type}
            onChange={setType}
            options={["mixed", ...classProfile.question_formats].map((code) => ({
              code,
              label: copy.formats[code] ?? code,
            }))}
            error={errors.question_type}
          />
        )}
        <SelectField
          name="language"
          label={text.language}
          value={language}
          onChange={setLanguage}
          options={languages}
          error={errors.language}
        />
      </div>
      {needsChapter && <p className="text-sm text-muted-foreground">{copy.tests.chooseChapter}</p>}
      <FormMessage message={state.message} />
      <SubmitButton size="lg" disabled={needsChapter} className="justify-self-start">
        {test ? copy.tests.create : text.submit}
      </SubmitButton>
    </form>
  );
}
