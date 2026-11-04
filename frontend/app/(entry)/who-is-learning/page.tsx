import Link from "next/link";
import { redirect } from "next/navigation";

import { ChildAvatar } from "@/components/child-avatar";
import { Button } from "@/components/ui/button";
import { getStudents } from "@/lib/api";
import { startChildMode } from "@/lib/actions/students";
import { classLabel } from "@/lib/copy";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.whoIsLearning.title);

/** The parent's home on a shared device: tap a child to start child mode. */
export default async function WhoIsLearningPage() {
  const copy = await getCopy();
  const text = copy.whoIsLearning;
  const children = await getStudents();
  if (children.length === 0) redirect("/onboarding/child");

  return (
    <div className="grid gap-8 text-center">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{text.title}</h1>
        <p className="text-muted-foreground">{text.subtitle}</p>
      </div>
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {children.map((child) => (
          <li key={child.id}>
            <form action={startChildMode.bind(null, child.id, {})}>
              <button
                type="submit"
                className="grid w-full justify-items-center gap-3 rounded-2xl border-2 bg-card p-6 transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                <ChildAvatar name={child.name} className="size-20 text-3xl" />
                <span className="font-display text-xl font-bold">{child.name}</span>
                <span className="text-sm text-muted-foreground">
                  {child.profile && classLabel(copy, child.profile)}
                </span>
              </button>
            </form>
          </li>
        ))}
        <li>
          <Link
            href="/parent/children/new"
            className="grid h-full w-full content-center justify-items-center gap-3 rounded-2xl border-2 border-dashed p-6 text-muted-foreground transition hover:border-primary hover:text-primary"
          >
            <span aria-hidden className="grid size-20 place-items-center rounded-full bg-muted text-4xl">
              +
            </span>
            <span className="font-display text-lg font-bold">{text.addChild}</span>
          </Link>
        </li>
      </ul>
      <Button asChild variant="outline" className="justify-self-center">
        <Link href="/parent/children">{text.parentArea}</Link>
      </Button>
    </div>
  );
}
