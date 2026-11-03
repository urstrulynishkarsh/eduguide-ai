import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getMe, getOptions } from "@/lib/api";
import { saveOwnProfile } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.onboarding.profileTitle };

/** A student who signed up alone: first-time class details, and later changes to them. */
export default async function OnboardingProfilePage() {
  const [me, options] = await Promise.all([getMe(), getOptions()]);
  // In child mode only the parent may change the class (from the parent area).
  if (me.user.role === "parent") redirect("/learn");
  return (
    <div className="grid gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.onboarding.profileTitle}</h1>
        <p className="text-muted-foreground">{copy.onboarding.profileSubtitle}</p>
      </div>
      <LearnerProfileForm
        options={options}
        action={saveOwnProfile}
        submitLabel={copy.onboarding.profileSubmit}
        student={me.active_student ?? undefined}
      />
    </div>
  );
}
