import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { PlanForm } from "@/components/plan-form";
import { getBooksWithChapters, getLearner, getPlan } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.plans;

export const metadata: Metadata = { title: text.newTitle };

/** A student who signed up alone makes their own plan. In child mode, the parent makes it. */
export default async function NewOwnPlanPage() {
  const { me, student } = await getLearner();
  if (me.user.role !== "student") redirect("/learn/plan");
  const [books, plan] = await Promise.all([getBooksWithChapters(), getPlan(student.id)]);
  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold dense:text-2xl">{text.newTitle}</h1>
        <p className="text-muted-foreground">{text.newSubtitle}</p>
      </div>
      <PlanForm area="learn" books={books} replaces={plan !== null} />
    </div>
  );
}
