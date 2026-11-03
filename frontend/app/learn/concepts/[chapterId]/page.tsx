import type { Metadata } from "next";
import Link from "next/link";

import { ExplainBox } from "@/components/explain-box";
import { getChapter } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.concepts.title };

export default async function ConceptPage({ params }: PageProps<"/learn/concepts/[chapterId]">) {
  const { chapterId } = await params;
  const chapter = await getChapter(chapterId);
  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <Link href="/learn/concepts" className="text-sm text-muted-foreground hover:underline">
          ← {copy.concepts.title}
        </Link>
        <h1 className="text-3xl font-extrabold dense:text-2xl">💡 {chapter.label}</h1>
      </div>
      <ExplainBox chapterId={chapter.id} />
    </div>
  );
}
