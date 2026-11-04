import Link from "next/link";

import { ColumnChart } from "@/components/charts";
import { StartButton } from "@/components/start-button";
import { testTitle } from "@/components/test-report";
import { Button } from "@/components/ui/button";
import { createPractice } from "@/lib/actions/practice";
import { reasonText, type Copy } from "@/lib/copy";
import { conceptHref } from "@/lib/navigation";
import type { Dashboard, Misconception } from "@/lib/types";
import { formatDay } from "@/lib/utils";

/** The last 7 days as columns: questions answered, the part right the first time in full colour. */
export function WeekChart({ week, copy }: { week: Dashboard["week"]; copy: Copy }) {
  const date = (iso: string, options: Intl.DateTimeFormatOptions) =>
    formatDay(copy.language.locale, iso, options);
  const columns = week.map((day) => ({
    key: day.day,
    tick: date(day.day, { weekday: "short" }),
    label: date(day.day, { weekday: "long", day: "numeric", month: "long" }),
    answered: day.answered,
    correct: day.correct,
  }));
  return <ColumnChart columns={columns} label={copy.dashboard.week} copy={copy} />;
}

/**
 * Today's Recommended for You. Each starts its practice as planned (topic, level); the first is
 * the one to start with. A learner may revise a weak topic's idea first.
 */
export function Recommendations({
  items,
  area,
  copy,
}: {
  items: Dashboard["recommendations"];
  area: "parent" | "learn";
  copy: Copy;
}) {
  const text = copy.dashboard;
  return (
    <ul className="grid gap-3">
      {items.map((item, i) => {
        const name = item.topic ?? item.chapter;
        const label = area === "parent" && i === 0 ? text.startRecommended : copy.start;
        return (
          <li
            key={item.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4 playful:rounded-3xl playful:border-4"
          >
            <div className="grid gap-1">
              <p className="font-semibold playful:text-2xl">{name}</p>
              <p className="text-sm text-muted-foreground playful:hidden">{reasonText(copy, item.reason)}</p>
            </div>
            {item.status === "done" ? (
              <span className="text-sm font-semibold text-success">{text.recommendationDone}</span>
            ) : (
              <div className="flex flex-wrap gap-2">
                {area === "learn" && item.revise?.chapter_id && (
                  <Button asChild variant="outline">
                    <Link href={conceptHref(item.revise)}>{copy.learn.revise}</Link>
                  </Button>
                )}
                <StartButton
                  action={createPractice.bind(null, area)}
                  fields={item.practice}
                  label={`${label}: ${name}`}
                  variant={i === 0 ? "default" : "outline"}
                  className="playful:h-16 playful:px-10 playful:text-2xl"
                >
                  {label}
                </StartButton>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** The last tests submitted, each opening its report. */
export function RecentTests({ tests, copy }: { tests: Dashboard["tests"]; copy: Copy }) {
  if (tests.length === 0) return <p className="text-muted-foreground">{copy.tests.none}</p>;
  return (
    <ul className="grid gap-2">
      {tests.map((test) => (
        <li key={test.attempt_id}>
          <Link
            href={`/parent/tests/${test.mock_test_id}?attempt=${test.attempt_id}`}
            className="flex flex-wrap justify-between gap-2 rounded-lg border bg-card px-4 py-3 hover:border-primary"
          >
            <span className="font-medium">{testTitle(copy, test.kind, test.place)}</span>
            <span className="text-sm text-muted-foreground">
              {test.score} / {test.total_marks} · {Math.round(test.percentage)}% ·{" "}
              {formatDay(copy.language.locale, test.submitted_at)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * Mistakes the child keeps making (Understand Mistakes), each with what to remember: a practice of its
 * topic, whose questions check it, and for the learner the idea explained again. Put right ones say so.
 */
export function Mistakes({
  items,
  area,
  copy,
}: {
  items: Misconception[];
  area: "parent" | "learn";
  copy: Copy;
}) {
  const text = copy.mistakes;
  return (
    <ul className="grid gap-3">
      {items.map((item) => {
        const place = item.topic ?? item.chapter;
        return (
          <li key={item.id} className="grid gap-2 rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <p className="font-semibold">{item.pattern}</p>
              <p className="text-sm text-muted-foreground">
                {place} · {text.seen(item.answers)}
              </p>
            </div>
            <p className="text-sm">
              <strong>{text.remember}</strong> {item.fix}
            </p>
            {item.status === "resolved" ? (
              <p className="text-sm font-semibold text-success">{text.fixed}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {area === "learn" && item.revise.chapter_id && (
                  <Button asChild variant="outline">
                    <Link href={conceptHref(item.revise)}>{copy.learn.revise}</Link>
                  </Button>
                )}
                <StartButton
                  action={createPractice.bind(null, area)}
                  fields={item.practice}
                  label={`${text.practise}: ${place}`}
                  variant="outline"
                >
                  {text.practise}
                </StartButton>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
