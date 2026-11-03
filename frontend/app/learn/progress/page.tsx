import type { Metadata } from "next";

import { ProgressView } from "@/components/progress-view";
import { getLearner, getProgress } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.progress.myTitle };

/** My progress; for Nursery – Class 2, My Stars. */
export default async function MyProgressPage() {
  const { student, classProfile } = await getLearner();
  const progress = await getProgress(student.id);
  const playful = classProfile.ui_mode === "playful";
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold playful:text-center playful:text-5xl dense:text-2xl">
        {playful ? `⭐ ${copy.progress.starsTitle}` : copy.progress.myTitle}
      </h1>
      <ProgressView progress={progress} stars={playful} sessionHref={(id) => `/learn/practice/${id}`} />
    </div>
  );
}
