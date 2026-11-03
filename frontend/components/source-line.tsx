import { copy } from "@/lib/copy";
import type { Source } from "@/lib/types";

/** Where a generated question or an explanation comes from (spec §42). Never claims to be the book's own. */
function sourceText(source: Source): string {
  const parts = [
    source.book_title,
    source.chapter,
    source.exercise && `${copy.practiceForm.exercise} ${source.exercise}`,
  ];
  const place = parts.filter(Boolean).join(" → ");
  return source.page ? `${place}, ${copy.chapter.page(source.page)}` : place;
}

export function SourceLine({ label, sources }: { label: string; sources: Source[] }) {
  return (
    <p className="text-xs text-muted-foreground">
      📘 {label} {sources.map(sourceText).join(" · ")}
    </p>
  );
}
