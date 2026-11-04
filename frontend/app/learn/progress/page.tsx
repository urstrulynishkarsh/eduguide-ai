import type { Metadata } from "next";

import { Mistakes } from "@/components/dashboard";
import { ProgressView } from "@/components/progress-view";
import { getLearner, getMisconceptions, getProgress } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.progress.myTitle };

/** My progress, and the mistakes to fix (from Class 3); for Nursery – Class 2, My Stars. */
export default async function MyProgressPage() {
  const { student, classProfile } = await getLearner();
  const [progress, mistakes] = await Promise.all([
    getProgress(student.id),
    classProfile.features.misconception_detection ? getMisconceptions(student.id) : [],
  ]);
  const playful = classProfile.ui_mode === "playful";
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold playful:text-center playful:text-5xl dense:text-2xl">
        {playful ? `⭐ ${copy.progress.starsTitle}` : copy.progress.myTitle}
      </h1>
      <ProgressView progress={progress} stars={playful} sessionHref={(id) => `/learn/practice/${id}`} />
      {mistakes.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-xl font-bold">{copy.mistakes.myTitle}</h2>
          <Mistakes items={mistakes} area="learn" />
        </section>
      )}
    </div>
  );
}
