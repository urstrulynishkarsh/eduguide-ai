import Link from "next/link";

import { PlanDays, PlanSummary, TaskActions, TaskLine } from "@/components/plan-view";
import { Button } from "@/components/ui/button";
import { getLearner, getPlan } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.plans.myTitle);

/**
 * The learner's study plan: today's tasks to start and tick off, then the days to come. A student
 * who signed up alone makes their own plan; a child's plan is made by the parent.
 */
export default async function LearnPlanPage() {
  const copy = await getCopy();
  const text = copy.plans;
  const { me, student } = await getLearner();
  const plan = await getPlan(student.id);
  const solo = me.user.role === "student";
  const today = plan?.days.find((day) => day.day === plan.planned_on)?.items ?? [];
  const comingUp = plan?.days.filter((day) => day.day > plan.planned_on) ?? [];

  return (
    <div className="grid max-w-3xl gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl font-extrabold dense:text-2xl">{text.myTitle}</h1>
        {solo && (
          <Button asChild variant={plan ? "outline" : "default"}>
            <Link href="/learn/plan/new">{plan ? text.makeNew : text.make}</Link>
          </Button>
        )}
      </div>
      {plan ? (
        <>
          <PlanSummary copy={copy} plan={plan} />
          <section className="grid gap-3">
            <h2 className="text-xl font-bold">{text.today}</h2>
            {today.length > 0 ? (
              <ul className="grid gap-2">
                {today.map((item) => (
                  <TaskLine copy={copy} key={item.id} item={item}>
                    <TaskActions copy={copy} item={item} />
                  </TaskLine>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground">{text.nothingToday}</p>
            )}
          </section>
          {comingUp.length > 0 && (
            <section className="grid gap-3">
              <h2 className="text-xl font-bold">{text.comingUp}</h2>
              <PlanDays copy={copy} days={comingUp} />
            </section>
          )}
        </>
      ) : (
        <p className="text-muted-foreground">{solo ? text.noneSolo : text.noneInChildMode}</p>
      )}
    </div>
  );
}
