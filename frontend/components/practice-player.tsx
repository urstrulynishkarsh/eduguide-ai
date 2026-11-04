"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { AnswerInput, answerFor, CHOICE, NUMBER, type Draft } from "@/components/answer-input";
import { FormMessage } from "@/components/form-message";
import { SourceLine } from "@/components/source-line";
import { Button } from "@/components/ui/button";
import { answerQuestion, explainQuestion, getHelp } from "@/lib/actions/practice";
import { copy } from "@/lib/copy";
import type { Result } from "@/lib/forms";
import type { AnswerResult, Explanation, Help, PracticeSession, UIMode } from "@/lib/types";
import { cn } from "@/lib/utils";

const text = copy.practice;

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
  // The youngest answer a choice or a count with one tap, without "Check".
  const oneTap = playful && [...CHOICE, ...NUMBER].includes(question.format);
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

        <AnswerInput
          question={question}
          draft={draft}
          disabled={final || pending}
          playful={playful}
          onChange={(next) => (oneTap ? submit(answerFor(question, next)) : setDraft(next))}
        />

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
            !oneTap && (
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
