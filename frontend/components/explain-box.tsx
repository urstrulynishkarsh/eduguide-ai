"use client";

import { useState, useTransition } from "react";

import { FormMessage } from "@/components/form-message";
import { SourceLine } from "@/components/source-line";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { setTaskStatus } from "@/lib/actions/plans";
import { explainConcept } from "@/lib/actions/practice";
import { copy } from "@/lib/copy";
import type { Explanation } from "@/lib/types";
import { cn } from "@/lib/utils";

const text = copy.concepts;

/**
 * "Explain this": a question about one chapter, answered from the learner's own books with sources.
 * A learn task of the study plan brings its question, and is ticked off once it is explained.
 */
export function ExplainBox({
  chapterId,
  studentId,
  initialQuestion = "",
  taskId,
}: {
  chapterId: string;
  studentId?: string;
  initialQuestion?: string;
  taskId?: string;
}) {
  const [question, setQuestion] = useState(initialQuestion);
  const [style, setStyle] = useState("normal");
  const [result, setResult] = useState<Explanation | null>(null);
  const [error, setError] = useState<string>();
  const [pending, startTransition] = useTransition();

  function ask(event: React.FormEvent) {
    event.preventDefault();
    startTransition(async () => {
      const answer = await explainConcept({ chapterId, studentId }, question, style);
      setResult("data" in answer ? answer.data : null);
      setError("error" in answer ? answer.error : undefined);
      if (taskId && "data" in answer) await setTaskStatus(taskId, "done");
    });
  }

  return (
    <div className="grid gap-4">
      <form onSubmit={ask} className="grid gap-3">
        <Label htmlFor="question">{text.ask}</Label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={text.askPlaceholder}
          required
          minLength={2}
          maxLength={1000}
          rows={2}
          className="rounded-md border border-input bg-card px-3 py-2 text-base shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <div className="flex flex-wrap gap-2" role="radiogroup">
          {Object.entries(text.styles).map(([code, label]) => (
            <button
              key={code}
              type="button"
              role="radio"
              aria-checked={style === code}
              onClick={() => setStyle(code)}
              className={cn(
                "rounded-full border bg-card px-3 py-1.5 text-sm font-medium",
                style === code && "border-primary bg-primary text-primary-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <Button type="submit" disabled={pending} className="justify-self-start">
          {pending ? copy.practice.busy : text.explain}
        </Button>
      </form>
      <FormMessage message={error} />
      {result && (
        <div className="grid gap-3 rounded-xl border bg-card p-5 shadow-sm">
          <p className="whitespace-pre-line">{result.explanation}</p>
          {result.steps.length > 0 && (
            <ol className="grid list-decimal gap-1 pl-5">
              {result.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}
          <SourceLine label={text.basedOn} sources={result.sources} />
        </div>
      )}
    </div>
  );
}
