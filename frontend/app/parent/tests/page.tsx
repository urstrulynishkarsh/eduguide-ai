import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { TestHeading } from "@/components/test-report";
import { Button } from "@/components/ui/button";
import { getTests, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { MockTest } from "@/lib/types";

const text = copy.tests;

export const metadata: Metadata = { title: text.title };

/** Where a test stands: being made, the latest score, or a sitting not finished. */
function standing(test: MockTest): string {
  if (test.status !== "ready")
    return test.status === "preparing" ? `⏳ ${text.preparingTitle}` : text.failedTitle;
  const sitting = test.attempts.at(-1);
  if (!sitting) return "";
  return sitting.submitted_at ? `${sitting.score} / ${test.total_marks}` : text.inProgress;
}

/** The chosen child's tests, newest first. */
export default async function ParentTestsPage() {
  const child = await requireChosenChild();
  const tests = await getTests(child.id);

  return (
    <div className="grid max-w-4xl gap-6">
      <AutoRefresh active={tests.some((test) => test.status === "preparing")} />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold">
            {text.title} · {child.name}
          </h1>
          <p className="text-muted-foreground">{text.subtitle(child.name)}</p>
        </div>
        <Button asChild>
          <Link href="/parent/tests/new">{text.create}</Link>
        </Button>
      </div>
      {tests.length === 0 ? (
        <p className="text-muted-foreground">{text.none}</p>
      ) : (
        <ul className="grid gap-3">
          {tests.map((test) => (
            <li key={test.id}>
              <Link
                href={`/parent/tests/${test.id}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4 hover:border-primary"
              >
                <TestHeading test={test} />
                <span className="font-semibold text-muted-foreground tabular-nums">{standing(test)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
