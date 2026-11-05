"use client";

import { useActionState, useState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Choice, ChoiceGroup, ErrorText, SelectField } from "@/components/choice";
import { Field, NO_AUTOFILL } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { said } from "@/lib/copy";
import type { FormState } from "@/lib/forms";
import type { OnboardingOptions, Student } from "@/lib/types";

/** Boards whose real name the backend keeps (board_name). */
const NAMED_BOARDS = ["state", "other"];

interface LearnerProfileFormProps {
  options: OnboardingOptions;
  action: (state: FormState, formData: FormData) => Promise<FormState>;
  submitLabel: string;
  /** The learner being edited, if any. */
  student?: Student;
  /** The child form also asks for name and age. */
  askName?: boolean;
}

/**
 * "Add Child" and "My class details". The class comes first: it decides which streams, goals and
 * subject suggestions are offered (all from /meta/options). The backend checks every rule again.
 */
export function LearnerProfileForm({
  options,
  action,
  submitLabel,
  student,
  askName,
}: LearnerProfileFormProps) {
  const copy = useCopy();
  const text = copy.profileForm;
  const [state, formAction] = useActionState(action, {});
  const profile = student?.profile;
  const errors = state.fieldErrors ?? {};

  const [classLevel, setClassLevel] = useState(profile?.class_level ?? "");
  const [name, setName] = useState(student?.name ?? "");
  const [age, setAge] = useState(student?.age?.toString() ?? "");
  const [board, setBoard] = useState(profile?.board ?? options.boards[0].code);
  const [boardName, setBoardName] = useState(profile?.board_name ?? "");
  const [medium, setMedium] = useState(profile?.medium ?? "en");
  const [language, setLanguage] = useState(profile?.primary_language ?? "en");
  const [stream, setStream] = useState(profile?.stream ?? "");
  const [goal, setGoal] = useState(profile?.goal ?? "");
  const [subjects, setSubjects] = useState<string[]>(profile?.subjects ?? []);
  const [newSubject, setNewSubject] = useState("");

  const chosenClass = options.classes.find((option) => option.class_level === classLevel);

  function chooseClass(code: string) {
    const next = options.classes.find((option) => option.class_level === code)!;
    setClassLevel(code);
    if (!next.requires_stream) setStream("");
    setGoal(next.default_goal);
  }

  function toggleSubject(subject: string) {
    setSubjects((current) =>
      current.includes(subject) ? current.filter((item) => item !== subject) : [...current, subject],
    );
  }

  function addSubject() {
    const subject = newSubject.trim().replace(/\s+/g, " ");
    if (subject && !subjects.some((item) => item.toLowerCase() === subject.toLowerCase())) {
      setSubjects([...subjects, subject]);
    }
    setNewSubject("");
  }

  const bands = [...new Set(options.classes.map((option) => option.band))];
  const suggestions =
    (stream && chosenClass?.suggested_subjects_by_stream?.[stream]) || chosenClass?.suggested_subjects || [];
  const subjectChoices = [...suggestions, ...subjects.filter((subject) => !suggestions.includes(subject))];
  const goalLabel = (code: string) =>
    said(copy.options.goals, code, options.goals.find((option) => option.code === code)?.label ?? code);

  return (
    <form action={formAction} className="grid gap-8">
      <fieldset className="grid gap-3">
        <legend className="mb-1 font-display text-lg font-bold">{text.classTitle}</legend>
        <p className="-mt-2 text-sm text-muted-foreground">{text.classHint}</p>
        {bands.map((band) => (
          <div key={band} className="grid gap-2">
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {text.bands[band] ?? band}
            </p>
            <div className="flex flex-wrap gap-2">
              {options.classes
                .filter((option) => option.band === band)
                .map((option) => (
                  <Choice
                    key={option.class_level}
                    name="class_level"
                    value={option.class_level}
                    label={said(copy.options.classes, option.class_level, option.label)}
                    checked={classLevel === option.class_level}
                    onChange={() => chooseClass(option.class_level)}
                  />
                ))}
            </div>
          </div>
        ))}
        <ErrorText error={errors.class_level} />
      </fieldset>

      {chosenClass && (
        <>
          {askName && (
            <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
              <Field
                name="name"
                label={text.childName}
                value={name}
                onChange={(event) => setName(event.target.value)}
                error={errors.name}
                required
                maxLength={80}
                autoComplete={NO_AUTOFILL}
              />
              <Field
                name="age"
                label={text.age}
                hint={text.ageHint}
                value={age}
                onChange={(event) => setAge(event.target.value)}
                error={errors.age}
                type="number"
                min={2}
                max={25}
              />
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              name="board"
              label={text.board}
              value={board}
              onChange={setBoard}
              options={options.boards.map(({ code, label }) => ({
                code,
                label: said(copy.options.boards, code, label),
              }))}
              error={errors.board}
            />
            {NAMED_BOARDS.includes(board) && (
              <Field
                name="board_name"
                label={text.boardName}
                placeholder={text.boardNamePlaceholder}
                value={boardName}
                onChange={(event) => setBoardName(event.target.value)}
                error={errors.board_name}
                maxLength={80}
                autoComplete={NO_AUTOFILL}
              />
            )}
            <SelectField
              name="medium"
              label={text.medium}
              value={medium}
              onChange={setMedium}
              options={options.mediums.map((option) => ({ code: option.code, label: option.label }))}
              error={errors.medium}
            />
          </div>

          <ChoiceGroup legend={text.language} error={errors.primary_language}>
            {options.languages.map((option) => (
              <Choice
                key={option.code}
                name="primary_language"
                value={option.code}
                label={
                  option.native_label === option.label
                    ? option.label
                    : `${option.label} · ${option.native_label}`
                }
                checked={language === option.code}
                onChange={() => setLanguage(option.code)}
              />
            ))}
          </ChoiceGroup>

          {chosenClass.requires_stream && (
            <ChoiceGroup legend={text.stream} error={errors.stream}>
              {options.streams.map((option) => (
                <Choice
                  key={option.code}
                  name="stream"
                  value={option.code}
                  label={said(copy.options.streams, option.code, option.label)}
                  checked={stream === option.code}
                  onChange={() => setStream(option.code)}
                />
              ))}
            </ChoiceGroup>
          )}

          <ChoiceGroup legend={text.goal} error={errors.goal}>
            {chosenClass.available_goals.map((code) => (
              <Choice
                key={code}
                name="goal"
                value={code}
                label={goalLabel(code)}
                checked={goal === code}
                onChange={() => setGoal(code)}
              />
            ))}
          </ChoiceGroup>

          <ChoiceGroup legend={text.subjects} hint={text.subjectsHint} error={errors.subjects}>
            {subjectChoices.map((subject) => (
              <Choice
                key={subject}
                type="checkbox"
                name="subjects"
                value={subject}
                label={subject}
                checked={subjects.includes(subject)}
                onChange={() => toggleSubject(subject)}
              />
            ))}
            <div className="flex w-full gap-2 sm:w-auto">
              <Input
                aria-label={text.addSubject}
                placeholder={text.addSubject}
                value={newSubject}
                maxLength={60}
                onChange={(event) => setNewSubject(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addSubject();
                  }
                }}
                className="sm:w-48"
              />
              <Button type="button" variant="outline" onClick={addSubject}>
                {text.add}
              </Button>
            </div>
          </ChoiceGroup>
        </>
      )}

      <FormMessage error={state} />
      <SubmitButton size="lg" disabled={!chosenClass} className="justify-self-start">
        {submitLabel}
      </SubmitButton>
    </form>
  );
}
