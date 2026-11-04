import Link from "next/link";

import { ConfirmButton } from "@/components/confirm-button";
import { PlanDays, PlanSummary } from "@/components/plan-view";
import { Button } from "@/components/ui/button";
import { deletePlan } from "@/lib/actions/plans";
import { getPlan, requireChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.plans.title);

/** The chosen child's study plan, day by day (one plan per learner). */
export default async function ParentPlansPage() {
  const copy = await getCopy();
  const text = copy.plans;
  const child = await requireChosenChild();
  const plan = await getPlan(child.id);

  return (
    <div className="grid max-w-4xl gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl font-extrabold">
          {text.title} · {child.name}
        </h1>
        <Button asChild>
          <Link href="/parent/plans/new">{plan ? text.makeNew : text.make}</Link>
        </Button>
      </div>
      {plan ? (
        <>
          <PlanSummary copy={copy} plan={plan} />
          <PlanDays copy={copy} days={plan.days} />
          <div>
            <ConfirmButton
              label={text.remove}
              confirmLabel={text.removeConfirm}
              action={deletePlan.bind(null, plan.id)}
            />
          </div>
        </>
      ) : (
        <p className="text-muted-foreground">{text.none(child.name)}</p>
      )}
    </div>
  );
}
