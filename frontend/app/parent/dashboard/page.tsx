import type { Metadata } from "next";
import Link from "next/link";

import { ProgressView } from "@/components/progress-view";
import { Button } from "@/components/ui/button";
import { getBooks, getProgress, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.dashboard;

export const metadata: Metadata = { title: copy.nav.dashboard };

/** The basic dashboard (Step 6). The full one, with strengths and recommendations, comes in Step 9. */
export default async function DashboardPage() {
  const child = await requireChosenChild();
  const [progress, books] = await Promise.all([getProgress(child.id), getBooks(child.id)]);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold">{text.title(child.name)}</h1>
          <p className="text-muted-foreground">
            {[child.profile?.class_label, text.books(books.length)].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/parent/books/upload">{text.uploadBook}</Link>
          </Button>
          <Button asChild>
            <Link href="/parent/practice">{text.createPractice}</Link>
          </Button>
        </div>
      </div>
      <ProgressView progress={progress} sessionHref={(id) => `/parent/practice/${id}`} />
    </div>
  );
}
