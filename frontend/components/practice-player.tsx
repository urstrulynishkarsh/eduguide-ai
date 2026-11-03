"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { FormMessage } from "@/components/form-message";
import { SourceLine } from "@/components/source-line";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { answerQuestion, explainQuestion, getHelp, type Result } from "@/lib/actions/practice";
import { copy } from "@/lib/copy";
import type { AnswerResult, Explanation, Help, PracticeSession, Question, UIMode } from "@/lib/types";
import { cn } from "@/lib/utils";

const text = copy.practice;
const CHOICE = ["mcq", "true_false", "assertion_reason", "case_based", "visual_choice"];
const NUMBER = ["numerical", "counting"];

type Draft = { option?: number; value?: string; text?: string; pairs?: (number | undefined)[] };

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

/**
 * One question at a time: answer, then Hint → Show Steps → Show Answer, and "explain this".
 * Nursery – Class 2 (`playful`): a tap answers, counting has a number pad, a wrong answer is an
 * invitation to try again, and there are no marks.
 */
export function PracticePlayer({ session, uiMode }: { session: PracticeSession; uiMode: UIMode }) {
  const router = useRouter();
  const playful = uiMode === "playful";
  const firstOpen = session.items.findIndex((item) => item.correct === null);
  const [index, setIndex] = useState(Math.max(firstOpen, 0));
  const [draft, setDraft] = useState<Draft>({});
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [help, setHelp] = useState<{ hints: string[]; hintsLeft: number; solution?: Help }>({
    hints: [],
    hintsLeft:
      session.items[Math.max(firstOpen, 0)].hints_total - session.items[Math.max(firstOpen, 0)].hints_shown,
  });
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [error, setError] = useState<string>();
  const [pending, startTransition] = useTransition();
  const shownAt = useRef(0);

  const item = session.items[index];
  const question = item.question;
  const final = result !== null && (result.correct || !result.try_again);
  const last = index === session.items.length - 1;

  useEffect(() => {
    shownAt.current = performance.now();
  }, [index]);

  function run<T>(call: () => Promise<Result<T>>, onData: (data: T) => void) {
    startTransition(async () => {
      const outcome = await call();
      if ("error" in outcome) setError(outcome.error);
      else {
        setError(undefined);
        onData(outcome.data);
      }
    });
  }

  function submit(answer: ReturnType<typeof answerFor>) {
    if (!answer || pending) return;
    run(
      () =>
        answerQuestion(
          session.id,
          { question_id: question.id, ...answer },
          performance.now() - shownAt.current,
        ),
      (data) => {
        setResult(data);
        if (data.try_again) setDraft({});
      },
    );
  }

  function askHelp(level: "hint" | "steps" | "answer") {
    run(
      () => getHelp(session.id, question.id, level),
      (data) =>
        setHelp((current) => ({
          hints: data.hint ? [...current.hints, data.hint] : current.hints,
          hintsLeft: data.hints_left,
          solution: level === "hint" ? current.solution : data,
        })),
    );
  }

  function next() {
    if (result?.session_completed || last) {
      router.refresh(); // the page shows the results once the session is complete
      return;
    }
    const upcoming = session.items[index + 1];
    setIndex(index + 1);
    setDraft({});
    setResult(null);
    setHelp({ hints: [], hintsLeft: upcoming.hints_total - upcoming.hints_shown });
    setExplanation(null);
    setError(undefined);
  }

  const optionClass = (chosen: boolean) =>
    cn(
      "rounded-lg border-2 bg-card px-4 py-3 text-left font-medium transition-colors hover:border-primary/60 disabled:cursor-default",
      "playful:grid playful:min-h-28 playful:place-items-center playful:rounded-3xl playful:text-center playful:text-2xl playful:font-bold",
      "friendly:rounded-2xl friendly:text-lg",
      chosen && "border-primary bg-secondary",
    );

  return (
    <div className="mx-auto grid max-w-3xl gap-6 playful:gap-8">
      <div className="grid gap-2">
        {!playful && (
          <p className="text-sm text-muted-foreground">{text.questionOf(index + 1, session.items.length)}</p>
        )}
        <div aria-hidden className="flex gap-1.5">
          {session.items.map((entry, i) => (
            <span
              key={entry.question.id}
              className={cn(
                "h-2 flex-1 rounded-full bg-muted playful:h-3",
                i < index && "bg-success/60",
                i === index && "bg-primary",
              )}
            />
          ))}
        </div>
      </div>

      <section
        aria-busy={pending}
        className="grid gap-4 rounded-2xl border bg-card p-5 shadow-sm playful:rounded-3xl playful:border-4 playful:p-8 sm:p-6"
      >
        {question.case && (
          <p className="rounded-lg bg-muted p-3 text-sm whitespace-pre-line">{question.case}</p>
        )}
        <h1 className="text-xl font-bold whitespace-pre-line playful:text-center playful:text-4xl friendly:text-2xl dense:text-lg">
          {question.text}
        </h1>

        {CHOICE.includes(question.format) && (
          <div
            className={cn(
              "grid gap-3",
              question.format === "visual_choice" || playful
                ? "grid-cols-1 sm:grid-cols-3"
                : "sm:grid-cols-2",
            )}
          >
            {question.options.map((option, i) => (
              <button
                key={option}
                type="button"
                aria-pressed={draft.option === i}
                disabled={final || pending}
                onClick={() => (playful ? submit({ option: i }) : setDraft({ option: i }))}
                className={optionClass(draft.option === i)}
              >
                {question.format === "visual_choice" ? <Picture option={option} /> : option}
              </button>
            ))}
          </div>
        )}

        {NUMBER.includes(question.format) &&
          (playful ? (
            <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
              {Array.from({ length: 11 }, (_, n) => (
                <button
                  key={n}
                  type="button"
                  disabled={final || pending}
                  onClick={() => submit({ value: n })}
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
                disabled={final}
                onChange={(event) => setDraft({ value: event.target.value })}
                className="max-w-48"
              />
              {question.unit && <span className="text-muted-foreground">{question.unit}</span>}
            </div>
          ))}

        {["fill_blank", "short_answer", "long_answer"].includes(question.format) &&
          (question.format === "fill_blank" ? (
            <Input
              aria-label={text.yourAnswer}
              placeholder={text.textPlaceholder}
              value={draft.text ?? ""}
              disabled={final}
              onChange={(event) => setDraft({ text: event.target.value })}
            />
          ) : (
            <textarea
              aria-label={text.yourAnswer}
              placeholder={text.textPlaceholder}
              rows={question.format === "long_answer" ? 7 : 3}
              value={draft.text ?? ""}
              disabled={final}
              onChange={(event) => setDraft({ text: event.target.value })}
              className="rounded-md border border-input bg-card px-3 py-2 shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          ))}

        {question.format === "matching" && (
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
                        disabled={final || pending}
                        onClick={() => {
                          const pairs = [...(draft.pairs ?? [])];
                          pairs[i] = j;
                          setDraft({ pairs });
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
        )}

        {result && (
          <div
            role="status"
            className={cn(
              "grid gap-1 rounded-xl p-4 font-semibold playful:text-center playful:text-3xl",
              result.correct ? "bg-success/10 text-success" : "bg-accent/30 text-accent-foreground",
            )}
          >
            <p>
              {result.correct
                ? playful
                  ? text.playfulCorrect
                  : text.correct
                : result.try_again
                  ? text.tryAgain
                  : text.wrong}
            </p>
            {result.correct_answer && !result.correct && (
              <p className="font-normal">{text.correctAnswer(result.correct_answer)}</p>
            )}
            {result.feedback && <p className="font-normal text-foreground">{result.feedback}</p>}
          </div>
        )}
        <FormMessage message={error} />

        <div className="flex flex-wrap gap-2">
          {final ? (
            <Button size="lg" onClick={next} className="playful:h-16 playful:px-10 playful:text-2xl">
              {result?.session_completed || last ? text.finish : text.next}
            </Button>
          ) : (
            !(playful && (CHOICE.includes(question.format) || NUMBER.includes(question.format))) && (
              <Button
                size="lg"
                disabled={!answerFor(question, draft) || pending}
                onClick={() => submit(answerFor(question, draft))}
                className="playful:h-16 playful:px-10 playful:text-2xl"
              >
                {pending ? text.busy : text.check}
              </Button>
            )
          )}
        </div>
      </section>

      <section aria-label={text.hint} className="grid gap-3">
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={pending || help.hintsLeft <= 0} onClick={() => askHelp("hint")}>
            💡 {text.hint}
            {!playful && (
              <span className="text-xs text-muted-foreground">({text.hintsLeft(help.hintsLeft)})</span>
            )}
          </Button>
          <Button
            variant="outline"
            disabled={pending || Boolean(help.solution)}
            onClick={() => askHelp("steps")}
          >
            🪜 {text.showSteps}
          </Button>
          <Button
            variant="outline"
            disabled={pending || Boolean(help.solution?.final_answer)}
            onClick={() => askHelp("answer")}
          >
            👀 {text.showAnswer}
          </Button>
        </div>
        {help.hints.map((hint) => (
          <p key={hint} className="rounded-lg border-l-4 border-accent bg-card p-3 playful:text-xl">
            💡 {hint}
          </p>
        ))}
        {help.solution && (
          <div className="grid gap-2 rounded-xl border bg-card p-4">
            {help.solution.concept && (
              <p>
                <strong>{text.concept}:</strong> {help.solution.concept}
              </p>
            )}
            {help.solution.steps.length > 0 && (
              <ol className="grid list-decimal gap-1 pl-5">
                {help.solution.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            )}
            {help.solution.final_answer && (
              <p>
                <strong>{text.finalAnswer}:</strong> {help.solution.final_answer}
              </p>
            )}
          </div>
        )}
      </section>

      {!playful && (
        <section className="grid gap-3">
          <h2 className="text-sm font-semibold text-muted-foreground">{text.explainTitle}</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(text.explainStyles).map(([style, label]) => (
              <Button
                key={style}
                variant="ghost"
                size="sm"
                disabled={pending}
                onClick={() => run(() => explainQuestion(session.id, question.id, style), setExplanation)}
              >
                {label}
              </Button>
            ))}
          </div>
          {explanation && (
            <div className="grid gap-2 rounded-xl border bg-card p-4">
              <p className="whitespace-pre-line">{explanation.explanation}</p>
              {explanation.steps.length > 0 && (
                <ol className="grid list-decimal gap-1 pl-5">
                  {explanation.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </section>
      )}

      <SourceLine label={text.generatedFrom} sources={[question.source]} />
    </div>
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
