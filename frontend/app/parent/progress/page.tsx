import { Mistakes, RecentTests } from "@/components/dashboard";
import { ProgressOverTime } from "@/components/progress-over-time";
import { ProgressView } from "@/components/progress-view";
import { BadgeList, RewardStrip } from "@/components/rewards";
import { getDashboard, getMisconceptions, getProgress, getTrends, requireChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.progress.title);

export default async function ParentProgressPage() {
  const copy = await getCopy();
  const child = await requireChosenChild();
  const [progress, board, mistakes, trends] = await Promise.all([
    getProgress(child.id),
    getDashboard(child.id),
    getMisconceptions(child.id),
    getTrends(child.id),
  ]);
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold">
        {copy.progress.title} · {child.name}
      </h1>
      <ProgressView copy={copy} progress={progress} area="parent" />
      <ProgressOverTime copy={copy} trends={trends} />
      <section className="grid gap-3">
        <h2 className="text-lg font-bold">{copy.rewards.title}</h2>
        <RewardStrip copy={copy} rewards={board.rewards} />
        <BadgeList copy={copy} badges={board.rewards.badges} />
      </section>
      {mistakes.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold">{copy.mistakes.title}</h2>
          <Mistakes copy={copy} items={mistakes} area="parent" />
        </section>
      )}
      {board.tests.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold">{copy.dashboard.recentTests}</h2>
          <RecentTests copy={copy} tests={board.tests} />
        </section>
      )}
    </div>
  );
}
