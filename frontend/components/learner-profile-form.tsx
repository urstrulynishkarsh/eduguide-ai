"use client";

import { useActionState, useState } from "react";

import { Field } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { copy } from "@/lib/copy";
import type { FormState } from "@/lib/forms";
import type { OnboardingOptions, Student } from "@/lib/types";
import { cn } from "@/lib/utils";

const text = copy.profileForm;
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
  const goalLabel = (code: string) => options.goals.find((option) => option.code === code)?.label ?? code;

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
                    label={option.label}
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
                autoComplete="off"
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
              options={options.boards}
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
                  label={option.label}
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

      <FormMessage message={state.message} />
      <SubmitButton size="lg" disabled={!chosenClass} className="justify-self-start">
        {submitLabel}
      </SubmitButton>
    </form>
  );
}

function ErrorText({ error }: { error?: string }) {
  return error ? <p className="text-sm text-destructive">{error}</p> : null;
}

function ChoiceGroup({
  legend,
  hint,
  error,
  children,
}: {
  legend: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="grid gap-2">
      <legend className="mb-2 text-sm font-medium">{legend}</legend>
      {hint && <p className="-mt-1 text-sm text-muted-foreground">{hint}</p>}
      <div className="flex flex-wrap gap-2">{children}</div>
      <ErrorText error={error} />
    </fieldset>
  );
}

/** A radio button or checkbox drawn as a tappable chip. */
function Choice({
  type = "radio",
  name,
  value,
  label,
  checked,
  onChange,
}: {
  type?: "radio" | "checkbox";
  name: string;
  value: string;
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="cursor-pointer">
      <input
        type={type}
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        className="peer sr-only"
      />
      <span
        className={cn(
          "inline-flex min-h-10 items-center rounded-full border bg-card px-4 text-sm font-medium transition-colors select-none",
          "hover:border-primary/50 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-primary-foreground",
          "peer-focus-visible:ring-[3px] peer-focus-visible:ring-ring/50",
        )}
      >
        {label}
      </span>
    </label>
  );
}

function SelectField({
  name,
  label,
  value,
  onChange,
  options,
  error,
}: {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { code: string; label: string }[];
  error?: string;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={name}>{label}</Label>
      <select
        id={name}
        name={name}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(error)}
        className="h-9 rounded-md border border-input bg-card px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {options.map((option) => (
          <option key={option.code} value={option.code}>
            {option.label}
          </option>
        ))}
      </select>
      <ErrorText error={error} />
    </div>
  );
}
