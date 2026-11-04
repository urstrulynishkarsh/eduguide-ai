import type { Metadata } from "next";

import { RecentTests } from "@/components/dashboard";
import { ProgressView } from "@/components/progress-view";
import { getDashboard, getProgress, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.progress.title };

export default async function ParentProgressPage() {
  const child = await requireChosenChild();
  const [progress, board] = await Promise.all([getProgress(child.id), getDashboard(child.id)]);
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold">
        {copy.progress.title} · {child.name}
      </h1>
      <ProgressView progress={progress} sessionHref={(id) => `/parent/practice/${id}`} />
      {board.tests.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold">{copy.dashboard.recentTests}</h2>
          <RecentTests tests={board.tests} />
        </section>
      )}
    </div>
  );
}
