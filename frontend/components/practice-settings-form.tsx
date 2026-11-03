"use client";

import { useActionState, useState } from "react";

import { Choice, ChoiceGroup, SelectField } from "@/components/choice";
import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { createPractice } from "@/lib/actions/practice";
import { copy } from "@/lib/copy";
import type { ClassProfile, Option } from "@/lib/types";

const text = copy.practiceForm;

/** Number, difficulty, type and language for a chosen place (spec §18). Limits come from the class. */
export function PracticeSettingsForm({
  area,
  place,
  classProfile,
  languages,
  defaultLanguage,
}: {
  area: "parent" | "learn";
  place: Record<"student_id" | "book_id" | "chapter_id" | "exercise_id", string | undefined>;
  classProfile: ClassProfile;
  languages: Option[];
  defaultLanguage: string;
}) {
  const [state, formAction] = useActionState(createPractice.bind(null, area), {});
  const [difficulty, setDifficulty] = useState("mixed");
  const [type, setType] = useState("mixed");
  const [language, setLanguage] = useState(defaultLanguage);
  const errors = state.fieldErrors ?? {};

  return (
    <form action={formAction} className="grid gap-6">
      {Object.entries(place).map(
        ([name, value]) => value && <input key={name} type="hidden" name={name} value={value} />,
      )}
      <div className="sm:w-48">
        <Field
          name="count"
          label={text.count}
          hint={text.countHint(classProfile.max_session_questions)}
          type="number"
          min={1}
          max={classProfile.max_session_questions}
          defaultValue={classProfile.default_session_questions}
          error={errors.count}
        />
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
        <SelectField
          name="language"
          label={text.language}
          value={language}
          onChange={setLanguage}
          options={languages}
          error={errors.language}
        />
      </div>
      <FormMessage message={state.message} />
      <SubmitButton size="lg" className="justify-self-start">
        {text.submit}
      </SubmitButton>
    </form>
  );
}
