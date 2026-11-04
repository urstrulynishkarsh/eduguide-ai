import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { placeOf, TestReportView, testTitle } from "@/components/test-report";
import { startChildMode } from "@/lib/actions/students";
import { getReport, getStudents, getTest } from "@/lib/api";
import { copy } from "@/lib/copy";
import { cn, formatDay } from "@/lib/utils";

const text = copy.tests;

export const metadata: Metadata = { title: text.title };

/**
 * A test the parent made: wait while its questions are written, hand the device to the child with
 * "Start now with …", then each sitting and its report (`?attempt=` picks one; the latest by default).
 */
export default async function ParentTestPage({ params, searchParams }: PageProps<"/parent/tests/[testId]">) {
  const [{ testId }, query] = await Promise.all([params, searchParams]);
  const [test, children] = await Promise.all([getTest(testId), getStudents()]);
  const name = children.find((child) => child.id === test.student_id)?.name ?? "";
  const submitted = test.attempts.filter((sitting) => sitting.submitted_at);
  const shown = submitted.find((sitting) => sitting.id === query.attempt) ?? submitted.at(-1);
  const report = shown && (await getReport(shown.id));

  return (
    <div className="grid max-w-4xl gap-6">
      <AutoRefresh active={test.status === "preparing"} />
      <div className="grid gap-1">
        <Link href="/parent/tests" className="text-sm text-muted-foreground hover:underline">
          ← {text.title}
        </Link>
        <h1 className="text-3xl font-extrabold">{testTitle(test.kind, placeOf(test))}</h1>
        <p className="text-muted-foreground">
          {text.summary(test.question_count, test.total_marks, test.duration_minutes)} ·{" "}
          {copy.difficulties[test.difficulty]}
        </p>
      </div>

      {test.status === "preparing" && (
        <div role="status" className="grid gap-2 rounded-xl border bg-card p-6 shadow-sm">
          <h2 className="text-2xl font-extrabold">⏳ {text.preparingTitle}</h2>
          <p className="text-muted-foreground">{copy.practice.preparingText}</p>
        </div>
      )}
      {test.status === "failed" && (
        <div className="grid gap-3">
          <h2 className="text-2xl font-extrabold">{text.failedTitle}</h2>
          <FormMessage message={test.error?.message} />
        </div>
      )}
      {test.status === "ready" && (
        <form action={startChildMode.bind(null, test.student_id, { test: test.id })}>
          <SubmitButton size="lg">{copy.practice.startNow(name)}</SubmitButton>
        </form>
      )}

      {test.attempts.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-xl font-bold">{text.sittings}</h2>
          <ul className="flex flex-wrap gap-2">
            {test.attempts.map((sitting) => {
              const label = `${formatDay(sitting.started_at)} · ${
                sitting.submitted_at ? `${sitting.score} / ${test.total_marks}` : text.inProgress
              }`;
              return (
                <li key={sitting.id}>
                  {sitting.submitted_at ? (
                    <Link
                      href={`?attempt=${sitting.id}`}
                      aria-current={sitting.id === shown?.id ? "true" : undefined}
                      className={cn(
                        "block rounded-full border bg-card px-4 py-1.5 text-sm font-medium hover:border-primary",
                        "aria-[current=true]:border-primary aria-[current=true]:bg-secondary",
                      )}
                    >
                      {label}
                    </Link>
                  ) : (
                    <span className="block rounded-full border px-4 py-1.5 text-sm text-muted-foreground">
                      {label}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {report && (
        <section className="grid gap-3">
          <h2 className="text-xl font-bold">{text.reportTitle}</h2>
          <TestReportView report={report} />
        </section>
      )}

      {test.status === "ready" && (
        <details className="grid gap-3">
          <summary className="cursor-pointer font-semibold text-primary">{text.seeQuestions}</summary>
          {test.sections.map((section) => (
            <section key={section.code} className="mt-3 grid gap-2">
              <h3 className="font-bold">{text.sectionTitle(section.code, section.title, section.marks)}</h3>
              <ol className="grid gap-2">
                {section.questions.map((question) => (
                  <li key={question.id} className="rounded-xl border bg-card p-4">
                    {question.case && (
                      <p className="mb-2 text-sm whitespace-pre-line text-muted-foreground">
                        {question.case}
                      </p>
                    )}
                    <p className="font-medium whitespace-pre-line">
                      {question.number}. {question.text}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </details>
      )}
    </div>
  );
}
