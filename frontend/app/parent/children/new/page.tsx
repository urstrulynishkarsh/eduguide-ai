import { LearnerProfileForm } from "@/components/learner-profile-form";
import { getOptions } from "@/lib/api";
import { addChild } from "@/lib/actions/students";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.parent.newChildTitle);

export default async function NewChildPage() {
  const copy = await getCopy();
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
