import type { Metadata } from "next";

import { ProgressView } from "@/components/progress-view";
import { getProgress, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.progress.title };

export default async function ParentProgressPage() {
  const child = await requireChosenChild();
  const progress = await getProgress(child.id);
  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-extrabold">
        {copy.progress.title} · {child.name}
      </h1>
      <ProgressView progress={progress} sessionHref={(id) => `/parent/practice/${id}`} />
    </div>
  );
}
