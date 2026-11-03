import type { Metadata } from "next";

import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getOptions } from "@/lib/api";
import { addChild } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.onboarding.childTitle };

/** The parent's first child, straight after sign-up. */
export default async function OnboardingChildPage() {
  const options = await getOptions();
  return (
    <div className="grid gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.onboarding.childTitle}</h1>
        <p className="text-muted-foreground">{copy.onboarding.childSubtitle}</p>
      </div>
      <LearnerProfileForm
        options={options}
        action={addChild.bind(null, "onboarding")}
        submitLabel={copy.onboarding.childSubmit}
        askName
      />
    </div>
  );
}
