import { Mistakes } from "@/components/dashboard";
import { ProgressOverTime } from "@/components/progress-over-time";
import { ProgressView } from "@/components/progress-view";
import { BadgeList, RewardStrip } from "@/components/rewards";
import { getLearner, getMisconceptions, getProgress, getRewards, getTrends } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.progress.myTitle);

/**
 * My progress over time, streak and badges, and the mistakes to fix (from Class 3); for Nursery –
 * Class 2, My Stars and stickers (no charts).
 */
export default async function MyProgressPage() {
  const copy = await getCopy();
  const { student, classProfile } = await getLearner();
  const playful = classProfile.ui_mode === "playful";
  const [progress, rewards, mistakes, trends] = await Promise.all([
    getProgress(student.id),
    getRewards(student.id),
    classProfile.features.misconception_detection ? getMisconceptions(student.id) : [],
    playful ? null : getTrends(student.id), // no charts for Nursery – Class 2
  ]);
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold playful:text-center playful:text-5xl dense:text-2xl">
        {playful ? `⭐ ${copy.progress.starsTitle}` : copy.progress.myTitle}
      </h1>
      <ProgressView copy={copy} progress={progress} area="learn" stars={playful} />
      {trends && (
        <ProgressOverTime copy={copy} trends={trends} simple={classProfile.ui_mode === "friendly"} />
      )}
      <RewardStrip copy={copy} rewards={rewards} playful={playful} />
      <section className="grid gap-3">
        <h2 className="text-xl font-bold playful:text-center playful:text-3xl">
          {playful ? copy.rewards.stickersTitle : copy.rewards.badgesTitle}
        </h2>
        <BadgeList copy={copy} badges={rewards.badges} />
      </section>
      {mistakes.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-xl font-bold">{copy.mistakes.myTitle}</h2>
          <Mistakes copy={copy} items={mistakes} area="learn" />
        </section>
      )}
    </div>
  );
}
