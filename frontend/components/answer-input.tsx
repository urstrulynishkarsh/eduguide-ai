"use client";

import { useCopy } from "@/components/copy-provider";
import { Input } from "@/components/ui/input";
import type { Answer, Question } from "@/lib/types";
import { cn } from "@/lib/utils";

/* Answering a question in each format: shared by practice and tests. */

export const CHOICE = ["mcq", "true_false", "assertion_reason", "case_based", "visual_choice"];
export const NUMBER = ["numerical", "counting"];

/** An answer being given; a number stays as typed until it is sent. */
export type Draft = { option?: number; value?: string; text?: string; pairs?: (number | undefined)[] };

/** "🍎 सेब" → a big picture and its word, for picture questions. */
export function pictureAndWord(option: string): { picture?: string; word: string } {
  const [first, ...rest] = [...new Intl.Segmenter().segment(option)].map((part) => part.segment);
  return /\p{Extended_Pictographic}/u.test(first ?? "")
    ? { picture: first, word: rest.join("").trim() }
    : { word: option };
}

/** The answer the API expects for this format (docs/03 §3.5), or null while it is incomplete. */
export function answerFor(question: Question, draft: Draft) {
  if (CHOICE.includes(question.format)) return draft.option === undefined ? null : { option: draft.option };
  if (NUMBER.includes(question.format)) {
    const value = Number(draft.value);
    return draft.value?.trim() && Number.isFinite(value) ? { value } : null;
  }
  if (question.format === "matching") {
    const pairs = draft.pairs ?? [];
    return question.match_left.every((_, i) => pairs[i] !== undefined) ? { pairs: pairs as number[] } : null;
  }
  return draft.text?.trim() ? { text: draft.text.trim() } : null;
}

/** An answer saved earlier (a test, after a reload) as a draft again. */
export function draftOf(answer: Answer): Draft {
  return {
    option: answer.option ?? undefined,
    value: answer.value?.toString(),
    text: answer.text ?? undefined,
    pairs: answer.pairs ?? undefined,
  };
}

const optionClass = (chosen: boolean) =>
  cn(
    "rounded-lg border-2 bg-card px-4 py-3 text-left font-medium transition-colors hover:border-primary/60 disabled:cursor-default",
    "playful:grid playful:min-h-28 playful:place-items-center playful:rounded-3xl playful:text-center playful:text-2xl playful:font-bold",
    "friendly:rounded-2xl friendly:text-lg",
    chosen && "border-primary bg-secondary",
  );

/**
 * The input that fits the question: options as buttons, a number, a blank, a written answer or
 * matching pairs. Nursery – Class 2 (`playful`) count on a number pad.
 */
export function AnswerInput({
  question,
  draft,
  onChange,
  disabled,
  playful = false,
}: {
  question: Question;
  draft: Draft;
  onChange: (draft: Draft) => void;
  disabled: boolean;
  playful?: boolean;
}) {
  const copy = useCopy();
  const text = copy.practice;
  if (CHOICE.includes(question.format)) {
    return (
      <div
        className={cn(
          "grid gap-3",
          question.format === "visual_choice" || playful ? "grid-cols-1 sm:grid-cols-3" : "sm:grid-cols-2",
        )}
      >
        {question.options.map((option, i) => (
          <button
            key={option}
            type="button"
            aria-pressed={draft.option === i}
            disabled={disabled}
            onClick={() => onChange({ option: i })}
            className={optionClass(draft.option === i)}
          >
            {question.format === "visual_choice" ? <Picture option={option} /> : option}
          </button>
        ))}
      </div>
    );
  }

  if (NUMBER.includes(question.format)) {
    return playful ? (
      <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
        {Array.from({ length: 11 }, (_, n) => (
          <button
            key={n}
            type="button"
            disabled={disabled}
            onClick={() => onChange({ value: String(n) })}
            className={optionClass(false)}
          >
            {n}
          </button>
        ))}
      </div>
    ) : (
      <div className="flex items-center gap-2">
        <Input
          aria-label={text.yourAnswer}
          type="number"
          step="any"
          inputMode="decimal"
          placeholder={text.numberPlaceholder}
          value={draft.value ?? ""}
          disabled={disabled}
          onChange={(event) => onChange({ value: event.target.value })}
          className="max-w-48"
        />
        {question.unit && <span className="text-muted-foreground">{question.unit}</span>}
      </div>
    );
  }

  if (question.format === "matching") {
    return (
      <div className="grid gap-4">
        {question.match_left.map((left, i) => (
          <div key={left} role="group" aria-label={text.matchPrompt(left)} className="grid gap-2">
            <p className="font-semibold playful:text-2xl">{text.matchPrompt(left)}</p>
            <div className="flex flex-wrap gap-2">
              {question.match_right.map((right, j) => {
                const chosen = draft.pairs?.[i] === j;
                return (
                  <button
                    key={right}
                    type="button"
                    aria-pressed={chosen}
                    disabled={disabled}
                    onClick={() => {
                      const pairs = [...(draft.pairs ?? [])];
                      pairs[i] = j;
                      onChange({ pairs });
                    }}
                    className={cn(
                      "rounded-full border-2 bg-card px-4 py-2 font-medium playful:px-6 playful:py-3 playful:text-xl",
                      chosen && "border-primary bg-secondary",
                    )}
                  >
                    {right}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return question.format === "fill_blank" ? (
    <Input
      aria-label={text.yourAnswer}
      placeholder={text.textPlaceholder}
      value={draft.text ?? ""}
      disabled={disabled}
      onChange={(event) => onChange({ text: event.target.value })}
    />
  ) : (
    <textarea
      aria-label={text.yourAnswer}
      placeholder={text.textPlaceholder}
      rows={question.format === "long_answer" ? 7 : 3}
      value={draft.text ?? ""}
      disabled={disabled}
      onChange={(event) => onChange({ text: event.target.value })}
      className="rounded-md border border-input bg-card px-3 py-2 shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
    />
  );
}

function Picture({ option }: { option: string }) {
  const { picture, word } = pictureAndWord(option);
  return (
    <span className="grid justify-items-center gap-1">
      {picture && (
        <span aria-hidden className="text-5xl leading-none playful:text-7xl">
          {picture}
        </span>
      )}
      <span>{word}</span>
    </span>
  );
}
