import Link from "next/link";

import { StartButton } from "@/components/start-button";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { setTaskStatus } from "@/lib/actions/plans";
import { createPractice } from "@/lib/actions/practice";
import { createTest } from "@/lib/actions/tests";
import { copy } from "@/lib/copy";
import type { PlanItem, StudyPlan } from "@/lib/types";
import { formatDay } from "@/lib/utils";

const text = copy.plans;
const EMOJI: Record<PlanItem["kind"], string> = { learn: "💡", practice: "✏️", test: "📝" };

function taskName(item: PlanItem): string {
  return item.kind === "test"
    ? text.wholeBook(item.book_title)
    : (item.topic ?? item.chapter ?? item.book_title);
}

/** Exam date, days left, tasks done, and what to change when not everything fits. */
export function PlanSummary({ plan }: { plan: StudyPlan }) {
  const line = [
    text.examOn(formatDay(plan.exam_date, { day: "numeric", month: "long", year: "numeric" })),
    text.daysLeft(plan.days_left),
    text.progress(plan.done, plan.total),
    plan.missed > 0 && text.missed(plan.missed),
    text.perDay(plan.daily_minutes),
  ];
  return (
    <div className="grid gap-3">
      <p className="text-muted-foreground">{line.filter(Boolean).join(" · ")}</p>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-success"
          style={{ width: `${(plan.done / Math.max(plan.total, 1)) * 100}%` }}
        />
      </div>
      {(plan.status === "finished" || plan.unscheduled > 0) && (
        <p role="status" className="rounded-md border border-accent bg-accent/20 px-3 py-2 text-sm">
          {plan.status === "finished" ? text.finished : text.unscheduled}
        </p>
      )}
    </div>
  );
}

/** A task: what, where, how long and why. `children` replaces its status (the learner's buttons). */
export function TaskLine({ item, children }: { item: PlanItem; children?: React.ReactNode }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4">
      <div className="grid gap-1">
        <p className="font-semibold">
          <span aria-hidden>{EMOJI[item.kind]}</span> {text.kinds[item.kind]}: {taskName(item)}
        </p>
        <p className="text-sm text-muted-foreground">
          {text.minutes(item.minutes)} · {item.reason}
        </p>
      </div>
      {children ?? (
        <span className="text-sm font-medium text-muted-foreground">{text.status[item.status]}</span>
      )}
    </li>
  );
}

/**
 * Start a task, or tick it off. A practice or a test is made from the task as planned (it is ticked
 * off by finishing it); a learn task opens Learn a Concept with its question filled in.
 */
export function TaskActions({ item }: { item: PlanItem }) {
  if (item.status === "done") {
    return (
      <form action={setTaskStatus.bind(null, item.id, "pending")} className="flex items-center gap-2">
        <span className="text-sm font-semibold text-success">✓ {text.status.done}</span>
        <SubmitButton variant="ghost" size="sm">
          {text.undo}
        </SubmitButton>
      </form>
    );
  }
  if (item.status !== "pending") {
    return <span className="text-sm font-medium text-muted-foreground">{text.status[item.status]}</span>;
  }
  const label = `${copy.start}: ${taskName(item)}`;
  return (
    <div className="flex flex-wrap gap-2">
      {item.practice && (
        <StartButton action={createPractice.bind(null, "learn")} fields={item.practice} label={label}>
          {copy.start}
        </StartButton>
      )}
      {item.test && (
        <StartButton action={createTest.bind(null, "learn")} fields={item.test} label={label}>
          {copy.start}
        </StartButton>
      )}
      {item.revise?.chapter_id && (
        <Button asChild>
          <Link
            href={`/learn/concepts/${item.revise.chapter_id}?q=${encodeURIComponent(item.revise.question)}&task=${item.id}`}
            aria-label={label}
          >
            {copy.start}
          </Link>
        </Button>
      )}
      <form action={setTaskStatus.bind(null, item.id, "done")}>
        <SubmitButton variant="outline">{text.markDone}</SubmitButton>
      </form>
    </div>
  );
}

/** The plan day by day (read only). */
export function PlanDays({ days }: { days: StudyPlan["days"] }) {
  return (
    <ol className="grid gap-5">
      {days.map((day) => (
        <li key={day.day} className="grid gap-2">
          <h3 className="font-bold">
            {formatDay(day.day, { weekday: "short", day: "numeric", month: "short" })}
            <span className="font-normal text-muted-foreground"> · {text.minutes(day.minutes)}</span>
          </h3>
          <ul className="grid gap-2">
            {day.items.map((item) => (
              <TaskLine key={item.id} item={item} />
            ))}
          </ul>
        </li>
      ))}
    </ol>
  );
}
