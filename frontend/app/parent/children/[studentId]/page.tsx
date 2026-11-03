import type { Metadata } from "next";

import { ChildAvatar } from "@/components/child-avatar";
import { ConfirmButton } from "@/components/confirm-button";
import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getOptions, getStudent } from "@/lib/api";
import { removeChild, updateChild } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

const text = copy.parent;

export const metadata: Metadata = { title: text.editTitle };

export default async function EditChildPage({ params }: PageProps<"/parent/children/[studentId]">) {
  const { studentId } = await params;
  const [child, options] = await Promise.all([getStudent(studentId), getOptions()]);

  return (
    <div className="grid max-w-3xl gap-8">
      <div className="flex items-center gap-4">
        <ChildAvatar name={child.name} className="size-14 text-2xl" />
        <div>
          <h1 className="text-3xl font-extrabold">{child.name}</h1>
          <p className="text-muted-foreground">{text.editTitle}</p>
        </div>
      </div>
      <LearnerProfileForm
        options={options}
        action={updateChild.bind(null, child.id)}
        submitLabel={text.save}
        student={child}
        askName
      />
      <section className="grid gap-3 rounded-xl border border-destructive/30 p-5">
        <h2 className="text-lg font-bold">{text.removeTitle}</h2>
        <p className="text-sm text-muted-foreground">{text.removeText(child.name)}</p>
        <ConfirmButton
          label={text.remove(child.name)}
          confirmLabel={text.removeConfirm}
          action={removeChild.bind(null, child.id)}
        />
      </section>
    </div>
  );
}
