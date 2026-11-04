import type { Metadata } from "next";
import Link from "next/link";

import { Recommendations, RecentTests, WeekChart } from "@/components/dashboard";
import { TaskLine } from "@/components/plan-view";
import { Bars } from "@/components/progress-view";
import { Button } from "@/components/ui/button";
import { getBooks, getDashboard, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { AreaMastery } from "@/lib/types";

const text = copy.dashboard;

export const metadata: Metadata = { title: copy.nav.dashboard };

/** Areas as bars of their mastery. */
const asBars = (areas: AreaMastery[]) =>
  areas.map((area) => ({
    id: `${area.chapter_id}${area.topic}`,
    name: area.topic ?? area.chapter,
    attempted: area.attempts,
    accuracy: area.mastery,
  }));

const card = "grid content-start gap-3 rounded-xl border bg-card p-5 shadow-sm";

/**
 * The chosen child at a glance: this week day by day, strong areas and those that need attention,
 * what to practise next (Start Recommended Practice), today's plan and the last tests.
 */
export default async function DashboardPage() {
  const child = await requireChosenChild();
  const [board, books] = await Promise.all([getDashboard(child.id), getBooks(child.id)]);
  const answered = board.week.reduce((sum, day) => sum + day.answered, 0);
  const minutes = board.week.reduce((sum, day) => sum + day.minutes, 0);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold">{text.title(child.name)}</h1>
          <p className="text-muted-foreground">
            {[child.profile?.class_label, text.books(books.length)].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/parent/books/upload">{text.uploadBook}</Link>
          </Button>
          <Button asChild>
            <Link href="/parent/practice">{text.createPractice}</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={card}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-bold">{text.week}</h2>
            <p className="text-sm text-muted-foreground">{text.weekTotal(answered, minutes)}</p>
          </div>
          <WeekChart week={board.week} />
        </section>
        {board.recommendations.length > 0 && (
          <section className="grid content-start gap-3">
            <h2 className="text-lg font-bold">{text.recommended}</h2>
            <Recommendations items={board.recommendations} area="parent" />
          </section>
        )}
      </div>

      {board.strong.length + board.needs_attention.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Bars title={text.needsAttention} areas={asBars(board.needs_attention)} />
          <Bars title={text.strong} areas={asBars(board.strong)} />
        </div>
      ) : (
        <p className="text-muted-foreground">{text.noAreas}</p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={card}>
          <h2 className="text-lg font-bold">{text.plan}</h2>
          {board.plan ? (
            <>
              <p className="text-sm text-muted-foreground">
                {text.planLine(board.plan.days_left, board.plan.done, board.plan.total)}
              </p>
              {board.plan.today.length > 0 ? (
                <ul className="grid gap-2">
                  {board.plan.today.map((item) => (
                    <TaskLine key={item.id} item={item} />
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">{copy.plans.nothingToday}</p>
              )}
              <Link href="/parent/plans" className="text-sm font-semibold text-primary hover:underline">
                {text.seePlan} →
              </Link>
            </>
          ) : (
            <>
              <p className="text-muted-foreground">{copy.plans.none(child.name)}</p>
              <Button asChild variant="outline" className="justify-self-start">
                <Link href="/parent/plans/new">{copy.plans.make}</Link>
              </Button>
            </>
          )}
        </section>
        <section className={card}>
          <h2 className="text-lg font-bold">{text.recentTests}</h2>
          <RecentTests tests={board.tests} />
          <Link href="/parent/tests" className="text-sm font-semibold text-primary hover:underline">
            {text.allTests} →
          </Link>
        </section>
      </div>
    </div>
  );
}
