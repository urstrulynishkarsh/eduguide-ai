import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { getBooks, getChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";
import { cn } from "@/lib/utils";

const text = copy.library;

export const metadata: Metadata = { title: text.title };

/** My Learning Library: every book of the family, labelled with the child it is for. */
export default async function LibraryPage() {
  const [{ children }, books] = await Promise.all([getChosenChild(), getBooks()]);
  const nameOf = (studentId: string | null) =>
    studentId ? text.forChild(children.find((c) => c.id === studentId)?.name ?? "") : text.forFamily;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold">{text.title}</h1>
          <p className="text-muted-foreground">{text.subtitle}</p>
        </div>
        <Button asChild>
          <Link href="/parent/books/upload">+ {text.upload}</Link>
        </Button>
      </div>
      {books.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">{text.empty}</p>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {books.map((book) => (
            <li key={book.id}>
              <Link
                href={`/parent/books/${book.id}`}
                className="grid gap-2 rounded-xl border bg-card p-5 shadow-sm transition hover:border-primary"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-lg font-bold">📘 {book.title}</h2>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold",
                      book.status === "ready" && "bg-success/10 text-success",
                      book.status === "processing" && "bg-secondary text-secondary-foreground",
                      (book.status === "failed" || book.status === "empty") &&
                        "bg-muted text-muted-foreground",
                    )}
                  >
                    {text.status[book.status]}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {[
                    book.subject,
                    book.class_label,
                    nameOf(book.student_id),
                    text.chapters(book.chapter_count),
                  ].join(" · ")}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
