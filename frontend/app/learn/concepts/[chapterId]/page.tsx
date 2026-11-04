import type { Metadata } from "next";
import Link from "next/link";

import { ExplainBox } from "@/components/explain-box";
import { getChapter } from "@/lib/api";
import { copy } from "@/lib/copy";
import { searchParam } from "@/lib/utils";

export const metadata: Metadata = { title: copy.concepts.title };

/** Learn a Concept for one chapter. `?q=` fills in the question; `?task=` is the plan's learn task. */
export default async function ConceptPage({
  params,
  searchParams,
}: PageProps<"/learn/concepts/[chapterId]">) {
  const [{ chapterId }, query] = await Promise.all([params, searchParams]);
  const chapter = await getChapter(chapterId);
  const [question, taskId] = [searchParam(query, "q"), searchParam(query, "task")];
  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <Link href="/learn/concepts" className="text-sm text-muted-foreground hover:underline">
          ← {copy.concepts.title}
        </Link>
        <h1 className="text-3xl font-extrabold dense:text-2xl">💡 {chapter.label}</h1>
      </div>
      {/* A new question or task starts the box afresh (a page visited before keeps its state). */}
      <ExplainBox
        key={`${question}:${taskId}`}
        chapterId={chapter.id}
        initialQuestion={question}
        taskId={taskId}
      />
    </div>
  );
}
