import Link from "next/link";

import { StartButton } from "@/components/start-button";
import { testTitle } from "@/components/test-report";
import { Button } from "@/components/ui/button";
import { createPractice } from "@/lib/actions/practice";
import { copy } from "@/lib/copy";
import { conceptHref } from "@/lib/navigation";
import type { Dashboard, Misconception } from "@/lib/types";
import { cn, formatDay } from "@/lib/utils";

const text = copy.dashboard;

/** The top of the scale: the busiest day, rounded up to a clean number (7 → 7, 23 → 30). */
function scaleTop(busiest: number): number {
  const most = Math.max(busiest, 1);
  const step = 10 ** Math.floor(Math.log10(most));
  return Math.ceil(most / step) * step;
}

/**
 * The last 7 days as columns: questions answered, the part right the first time in full blue. A
 * day shows its numbers on hover, focus or tap, and screen readers hear them.
 */
export function WeekChart({ week }: { week: Dashboard["week"] }) {
  const top = scaleTop(Math.max(...week.map((day) => day.answered)));
  return (
    <figure className="grid gap-3">
      <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        {[
          ["bg-primary", text.right],
          ["bg-primary-light", text.notRight],
        ].map(([colour, label]) => (
          <li key={label} className="flex items-center gap-1.5">
            <span aria-hidden className={cn("size-2.5 rounded-[2px]", colour)} />
            {label}
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-[auto_1fr] gap-x-2 pt-7">
        <div aria-hidden className="flex flex-col justify-between text-xs text-muted-foreground tabular-nums">
          <span className="-mt-2">{top}</span>
          <span className="-mb-2">0</span>
        </div>
        {/* The readout sits above the plot, so it never runs off the card. */}
        <div role="group" aria-label={text.week} className="relative flex h-32 items-end border-y">
          {week.map((day) => (
            <div
              key={day.day}
              role="img"
              tabIndex={0}
              aria-label={text.dayLine(
                formatDay(day.day, { weekday: "long", day: "numeric", month: "long" }),
                day.answered,
                day.correct,
              )}
              className="group flex h-full flex-1 items-end justify-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            >
              {day.answered > 0 && (
                <span
                  className="flex w-full max-w-6 flex-col gap-[2px] overflow-hidden rounded-t-[4px] group-hover:opacity-80 group-focus:opacity-80"
                  style={{ height: `${(day.answered / top) * 100}%` }}
                >
                  {day.answered > day.correct && (
                    <span className="bg-primary-light" style={{ flexGrow: day.answered - day.correct }} />
                  )}
                  {day.correct > 0 && <span className="bg-primary" style={{ flexGrow: day.correct }} />}
                </span>
              )}
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 -top-7 hidden text-center text-xs font-medium group-hover:block group-focus:block"
              >
                {text.dayLine(
                  formatDay(day.day, { weekday: "short", day: "numeric" }),
                  day.answered,
                  day.correct,
                )}
              </span>
            </div>
          ))}
        </div>
        <span />
        <div aria-hidden className="flex pt-1 text-xs text-muted-foreground">
          {week.map((day) => (
            <span key={day.day} className="flex-1 text-center">
              {formatDay(day.day, { weekday: "short" })}
            </span>
          ))}
        </div>
      </div>
    </figure>
  );
}

/**
 * Today's Recommended for You. Each starts its practice as planned (topic, level); the first is
 * the one to start with. A learner may revise a weak topic's idea first.
 */
export function Recommendations({
  items,
  area,
}: {
  items: Dashboard["recommendations"];
  area: "parent" | "learn";
}) {
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
              <p className="text-sm text-muted-foreground playful:hidden">{item.reason}</p>
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
export function RecentTests({ tests }: { tests: Dashboard["tests"] }) {
  if (tests.length === 0) return <p className="text-muted-foreground">{copy.tests.none}</p>;
  return (
    <ul className="grid gap-2">
      {tests.map((test) => (
        <li key={test.attempt_id}>
          <Link
            href={`/parent/tests/${test.mock_test_id}?attempt=${test.attempt_id}`}
            className="flex flex-wrap justify-between gap-2 rounded-lg border bg-card px-4 py-3 hover:border-primary"
          >
            <span className="font-medium">{testTitle(test.kind, test.place)}</span>
            <span className="text-sm text-muted-foreground">
              {test.score} / {test.total_marks} · {Math.round(test.percentage)}% ·{" "}
              {formatDay(test.submitted_at)}
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
export function Mistakes({ items, area }: { items: Misconception[]; area: "parent" | "learn" }) {
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
