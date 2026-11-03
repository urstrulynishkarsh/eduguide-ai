import type { Metadata } from "next";

import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getOptions } from "@/lib/api";
import { addChild } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.parent.newChildTitle };

export default async function NewChildPage() {
  const options = await getOptions();
  return (
    <div className="grid max-w-3xl gap-6">
      <h1 className="text-3xl font-extrabold">{copy.parent.newChildTitle}</h1>
      <LearnerProfileForm
        options={options}
        action={addChild.bind(null, "parent")}
        submitLabel={copy.onboarding.childSubmit}
        askName
      />
    </div>
  );
}
