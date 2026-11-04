import { PlanForm } from "@/components/plan-form";
import { getBooksWithChapters, getPlan, requireChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.plans.newTitle);

export default async function NewPlanPage() {
  const copy = await getCopy();
  const text = copy.plans;
  const child = await requireChosenChild();
  const [books, plan] = await Promise.all([getBooksWithChapters(child.id), getPlan(child.id)]);
  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">
          {text.newTitle} · {child.name}
        </h1>
        <p className="text-muted-foreground">{text.newSubtitle}</p>
      </div>
      <PlanForm area="parent" studentId={child.id} books={books} replaces={plan !== null} />
    </div>
  );
}
