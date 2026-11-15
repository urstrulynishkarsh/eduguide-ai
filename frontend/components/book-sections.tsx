import Link from "next/link";

import { BookUploader } from "@/components/book-uploader";
import { ConfirmButton } from "@/components/confirm-button";
import { DocumentChecklist } from "@/components/document-checklist";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { deleteBook, removeDocument, retryDocument } from "@/lib/actions/books";
import { classLabel, type Copy } from "@/lib/copy";
import type { Book, Chapter, OnboardingOptions } from "@/lib/types";
import { cn } from "@/lib/utils";

/* The pieces of a library, shared by the parent's (/parent/books) and a solo student's (/learn/books). */

type Area = "parent" | "learn";

/** The books, each with its status and a line of details; `detail` adds who a book is for. */
export function BookList({
  books,
  copy,
  area,
  detail,
}: {
  books: Book[];
  copy: Copy;
  area: Area;
  detail?: (book: Book) => string;
}) {
  const text = copy.library;
  if (books.length === 0) {
    return (
      <p className="rounded-xl border border-dashed p-8 text-center text-muted-foreground">{text.empty}</p>
    );
  }
  return (
    <ul className={cn("grid gap-4", area === "parent" && "md:grid-cols-2")}>
      {books.map((book) => (
        <li key={book.id}>
          <Link
            href={`/${area}/books/${book.id}`}
            className="grid gap-2 rounded-xl border bg-card p-5 shadow-sm transition hover:border-primary"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 className="text-lg font-bold">📘 {book.title}</h2>
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold",
                  book.status === "ready" && "bg-success/10 text-success",
                  book.status === "processing" && "bg-secondary text-secondary-foreground",
                  (book.status === "failed" || book.status === "empty") && "bg-muted text-muted-foreground",
                )}
              >
                {text.status[book.status]}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {[book.subject, classLabel(copy, book), detail?.(book), text.chapters(book.chapter_count)]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** A book's chapters (a book of papers: its papers), each a link to `href`. */
export function BookChapters({
  chapters,
  copy,
  isPapers,
  href,
}: {
  chapters: Chapter[];
  copy: Copy;
  isPapers: boolean;
  href: (chapter: Chapter) => string;
}) {
  const text = copy.library;
  return (
    <section className="grid gap-3">
      <h2 className="text-xl font-bold">{isPapers ? text.papersTitle : text.chaptersTitle}</h2>
      {chapters.length === 0 ? (
        <p className="text-muted-foreground">{text.noChapters}</p>
      ) : (
        <ul className="grid gap-2">
          {chapters.map((chapter) => (
            <li key={chapter.id}>
              <Link
                href={href(chapter)}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card px-4 py-3 hover:border-primary"
              >
                <span className="font-semibold">{chapter.label}</span>
                <span className="text-sm text-muted-foreground">
                  {isPapers ? copy.chapter.sections : copy.chapter.exercises}: {chapter.exercise_count} ·{" "}
                  {copy.chapter.questions(chapter.question_count)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Whether any file of the book is still being read (the page then reloads until it is done). */
export const isReading = (book: Book) =>
  book.documents.some((document) => document.status === "queued" || document.status === "processing");

/** The book's files with their reading checklist (retry, remove), and Add another file. */
export function BookFiles({
  book,
  copy,
  area,
  limits,
}: {
  book: Book;
  copy: Copy;
  area: Area;
  limits: OnboardingOptions["upload"];
}) {
  const text = copy.library;
  const reading = isReading(book);
  return (
    <section className="grid gap-3">
      <h2 className="text-xl font-bold">{text.files}</h2>
      <ul className="grid gap-3">
        {book.documents.map((document) => (
          <li key={document.id} className="grid gap-3 rounded-xl border bg-card p-4 shadow-sm">
            <p className="font-medium break-all">{document.original_filename}</p>
            <DocumentChecklist copy={copy} document={document} />
            {document.status === "ready" && (
              <p className="text-sm text-success">
                {text.found(
                  document.summary.chapters ?? 0,
                  document.summary.exercises ?? 0,
                  document.summary.questions ?? 0,
                )}
              </p>
            )}
            <FormMessage error={document.error} />
            <div className="flex flex-wrap gap-2">
              {document.status === "failed" && (
                <form action={retryDocument.bind(null, document.id)}>
                  <SubmitButton variant="outline" size="sm">
                    {text.retry}
                  </SubmitButton>
                </form>
              )}
              {!reading && (
                <form action={removeDocument.bind(null, document.id)}>
                  <SubmitButton variant="ghost" size="sm" className="text-muted-foreground">
                    {text.removeFile}
                  </SubmitButton>
                </form>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="rounded-xl border border-dashed p-4">
        <h3 className="mb-3 font-bold">{text.addFile}</h3>
        <BookUploader area={area} bookId={book.id} limits={limits} />
      </div>
    </section>
  );
}

/** Delete this book, asked twice; the library of `area` follows. */
export function DeleteBook({ book, copy, area }: { book: Book; copy: Copy; area: Area }) {
  const text = copy.library;
  return (
    <section className="grid gap-3 rounded-xl border border-destructive/30 p-5">
      <h2 className="text-lg font-bold">{text.deleteBook}</h2>
      <p className="text-sm text-muted-foreground">{text.deleteBookText}</p>
      <ConfirmButton
        label={text.deleteBook}
        confirmLabel={text.deleteConfirm}
        action={deleteBook.bind(null, area, book.id)}
      />
    </section>
  );
}
