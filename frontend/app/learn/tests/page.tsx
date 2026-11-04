import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { chosenFrom, TestChooser } from "@/components/question-chooser";
import { SubmitButton } from "@/components/submit-button";
import { TestHeading } from "@/components/test-report";
import { Button } from "@/components/ui/button";
import { startTest } from "@/lib/actions/tests";
import { getBooks, getLearner, getOptions, getTests } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.tests;

export const metadata: Metadata = { title: text.myTitle };

/** The learner's tests: start one, carry on, see the result or take it again; and Create Test. */
export default async function LearnTestsPage({ searchParams }: PageProps<"/learn/tests">) {
  const [{ student, profile, classProfile }, query, options, books] = await Promise.all([
    getLearner(),
    searchParams,
    getOptions(),
    getBooks(),
  ]);
  const tests = await getTests(student.id);

  return (
    <div className="grid max-w-3xl gap-8">
      <AutoRefresh active={tests.some((test) => test.status === "preparing")} />
      <h1 className="text-3xl font-extrabold dense:text-2xl">{text.myTitle}</h1>
      {tests.length === 0 ? (
        <p className="text-muted-foreground">{text.none}</p>
      ) : (
        <ul className="grid gap-3">
          {tests.map((test) => {
            const sitting = test.attempts.at(-1);
            return (
              <li
                key={test.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4"
              >
                <TestHeading test={test} />
                {test.status === "preparing" && (
                  <p role="status" className="text-sm text-muted-foreground">
                    ⏳ {text.preparingTitle}
                  </p>
                )}
                {test.status === "failed" && <p className="text-sm text-destructive">{text.failedTitle}</p>}
                {test.status === "ready" && (
                  <div className="flex flex-wrap gap-2">
                    {sitting?.submitted_at && (
                      <Button asChild variant="outline">
                        <Link href={`/learn/tests/${sitting.id}`}>
                          {text.result} · {sitting.score} / {test.total_marks}
                        </Link>
                      </Button>
                    )}
                    <form action={startTest.bind(null, test.id)}>
                      <SubmitButton>
                        {!sitting ? text.start : sitting.submitted_at ? text.retake : text.continue}
                      </SubmitButton>
                    </form>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <section className="grid gap-4">
        <h2 className="text-xl font-bold">{text.create}</h2>
        <TestChooser
          area="learn"
          books={books}
          chosen={chosenFrom(query)}
          classProfile={classProfile}
          languages={options.languages}
          defaultLanguage={profile.primary_language}
        />
      </section>
    </div>
  );
}
