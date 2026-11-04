"use client";

import { useRouter } from "next/navigation";
import { useEffect, useEffectEvent, useRef, useState } from "react";

import { AnswerInput, answerFor, CHOICE, draftOf, type Draft } from "@/components/answer-input";
import { FormMessage } from "@/components/form-message";
import { Button } from "@/components/ui/button";
import { saveTestAnswer, submitTest } from "@/lib/actions/tests";
import { copy } from "@/lib/copy";
import type { Question, TestAttempt } from "@/lib/types";
import { cn } from "@/lib/utils";

const text = copy.tests;
/** A call that did not get through (the connection dropped): said, and the screen carries on. */
const offline = () => ({ error: copy.errors.unreachable });

/** 754 → "12:34"; 3754 → "1:02:34". */
export function clock(seconds: number): string {
  const [h, m, s] = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60];
  const pad = (n: number) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

/** Counts down from the seconds the backend said were left, and says when they run out. */
function Countdown({ seconds, onEnd }: { seconds: number; onEnd: () => void }) {
  const [left, setLeft] = useState(seconds);
  const end = useEffectEvent(onEnd);
  useEffect(() => {
    const endsAt = Date.now() + seconds * 1000;
    const tick = setInterval(() => {
      const next = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      setLeft(next);
      if (next === 0) {
        clearInterval(tick);
        end();
      }
    }, 1000);
    return () => clearInterval(tick);
  }, [seconds]);
  return (
    <p
      role="timer"
      aria-label={text.timeLeft}
      className={cn("font-mono text-lg font-bold tabular-nums", left < 300 && "text-destructive")}
    >
      ⏱ {clock(left)}
    </p>
  );
}

/**
 * A test being taken: a question at a time, a grid to jump between them, and the time left when the
 * test is timed. Each answer is saved as it is given (a choice at once, typing when it pauses), so a
 * reload loses nothing; it can be changed until the test is submitted, by the button or when the
 * time runs out. The page then shows the report.
 */
export function TestPlayer({ attempt, title }: { attempt: TestAttempt; title: string }) {
  const router = useRouter();
  const items = attempt.sections.flatMap((section) =>
    section.questions.map((question) => ({ question, section })),
  );
  const [index, setIndex] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Draft>>(() =>
    Object.fromEntries(Object.entries(attempt.responses).map(([id, answer]) => [id, draftOf(answer)])),
  );
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  // Answers not sent yet, and the saves in order (a later answer must not arrive first).
  const unsaved = useRef(new Map<string, { draft: Draft; timer: ReturnType<typeof setTimeout> }>());
  const saves = useRef(Promise.resolve());

  const { question, section } = items[index];
  const draft = drafts[question.id] ?? {};
  const answered = items.filter((item) => answerFor(item.question, drafts[item.question.id] ?? {})).length;

  function save(item: Question) {
    const entry = unsaved.current.get(item.id);
    if (!entry) return;
    clearTimeout(entry.timer);
    unsaved.current.delete(item.id);
    const answer = answerFor(item, entry.draft);
    if (!answer) return; // an emptied box: the answer saved before stays
    saves.current = saves.current.then(async () => {
      const result = await saveTestAnswer(attempt.id, item.id, answer).catch(offline);
      setError("error" in result ? result.error : undefined);
    });
  }

  function change(next: Draft) {
    setDrafts((current) => ({ ...current, [question.id]: next }));
    clearTimeout(unsaved.current.get(question.id)?.timer);
    const delay = CHOICE.includes(question.format) ? 0 : 1000;
    unsaved.current.set(question.id, { draft: next, timer: setTimeout(() => save(question), delay) });
  }

  async function submit() {
    setChecking(false);
    setSubmitting(true);
    items.forEach((item) => save(item.question));
    await saves.current;
    const result = await submitTest(attempt.id).catch(offline);
    if ("error" in result) {
      setError(result.error);
      setSubmitting(false);
    } else router.refresh(); // the page shows the report
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <div className="sticky top-0 z-10 -mx-4 flex flex-wrap items-center justify-between gap-3 border-b bg-background/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border">
        <div className="grid">
          <h1 className="font-display text-lg font-bold">{title}</h1>
          <p className="text-sm text-muted-foreground">{text.answered(answered, items.length)}</p>
        </div>
        <div className="flex items-center gap-3">
          {attempt.seconds_left !== null && <Countdown seconds={attempt.seconds_left} onEnd={submit} />}
          <Button onClick={() => setChecking(true)} disabled={submitting}>
            {text.submit}
          </Button>
        </div>
      </div>

      {(checking || submitting) && (
        <div role="status" className="grid gap-3 rounded-xl border bg-card p-4">
          <p className="font-semibold">
            {submitting ? text.marking : text.submitCheck(items.length - answered)}
          </p>
          {!submitting && (
            <div className="flex flex-wrap gap-2">
              <Button onClick={submit}>{text.submitYes}</Button>
              <Button variant="ghost" onClick={() => setChecking(false)}>
                {copy.cancel}
              </Button>
            </div>
          )}
        </div>
      )}
      <FormMessage message={error} />

      <nav aria-label={text.grid} className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <button
            key={item.question.id}
            type="button"
            aria-current={i === index ? "step" : undefined}
            onClick={() => setIndex(i)}
            className={cn(
              "size-9 rounded-md border bg-card text-sm font-semibold tabular-nums",
              answerFor(item.question, drafts[item.question.id] ?? {}) && "border-primary bg-secondary",
              i === index && "ring-2 ring-primary",
            )}
          >
            {i + 1}
          </button>
        ))}
      </nav>

      <section className="grid gap-4 rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
        <p className="text-sm font-semibold text-muted-foreground">
          {text.sectionTitle(section.code, section.title, section.marks)}
        </p>
        {question.case && (
          <p className="rounded-lg bg-muted p-3 text-sm whitespace-pre-line">{question.case}</p>
        )}
        <h2 className="text-xl font-bold whitespace-pre-line friendly:text-2xl dense:text-lg">
          {index + 1}. {question.text}
        </h2>
        <AnswerInput question={question} draft={draft} disabled={submitting} onChange={change} />
      </section>

      <div className="flex justify-between gap-2">
        <Button variant="outline" disabled={index === 0} onClick={() => setIndex(index - 1)}>
          ← {text.previous}
        </Button>
        <Button variant="outline" disabled={index === items.length - 1} onClick={() => setIndex(index + 1)}>
          {text.next} →
        </Button>
      </div>
    </div>
  );
}
