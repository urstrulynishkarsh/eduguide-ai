import type { Metadata } from "next";
import Link from "next/link";

import { ChildAvatar } from "@/components/child-avatar";
import { SubmitButton } from "@/components/submit-button";
import { Button } from "@/components/ui/button";
import { getOptions, getStudents } from "@/lib/api";
import { startChildMode } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

const text = copy.parent;

export const metadata: Metadata = { title: text.childrenTitle };

export default async function ChildrenPage() {
  const [children, options] = await Promise.all([getStudents(), getOptions()]);
  const label = (list: { code: string; label: string }[], code: string) =>
    list.find((option) => option.code === code)?.label ?? code;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold">{text.childrenTitle}</h1>
          <p className="text-muted-foreground">{text.childrenSubtitle}</p>
        </div>
        <Button asChild>
          <Link href="/parent/children/new">+ {text.addChild}</Link>
        </Button>
      </div>

      <ul className="grid gap-4 md:grid-cols-2">
        {children.map((child) => (
          <li key={child.id} className="grid gap-4 rounded-xl border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-4">
              <ChildAvatar name={child.name} />
              <div className="grid gap-0.5">
                <h2 className="text-xl font-bold">{child.name}</h2>
                <p className="text-sm text-muted-foreground">
                  {child.profile
                    ? [child.profile.class_label, label(options.boards, child.profile.board)].join(" · ")
                    : text.noProfile}
                </p>
                {child.profile && (
                  <p className="text-sm text-muted-foreground">
                    {text.goal}: {label(options.goals, child.profile.goal)}
                  </p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <form action={startChildMode.bind(null, child.id, {})}>
                <SubmitButton>{text.startLearning}</SubmitButton>
              </form>
              <Button asChild variant="outline">
                <Link href={`/parent/children/${child.id}`}>{text.edit}</Link>
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
