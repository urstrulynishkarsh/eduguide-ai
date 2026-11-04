import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getOptions } from "@/lib/api";
import { addChild } from "@/lib/actions/students";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.onboarding.childTitle);

/** The parent's first child, straight after sign-up. */
export default async function OnboardingChildPage() {
  const copy = await getCopy();
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
