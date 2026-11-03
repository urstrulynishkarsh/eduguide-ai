import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { BookUploader } from "@/components/book-uploader";
import { ConfirmButton } from "@/components/confirm-button";
import { DocumentChecklist } from "@/components/document-checklist";
import { FormMessage } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { getBook, getChapters, getOptions } from "@/lib/api";
import { deleteBook, removeDocument, retryDocument } from "@/lib/actions/books";
import { copy } from "@/lib/copy";

const text = copy.library;

export const metadata: Metadata = { title: text.title };

export default async function BookPage({ params }: PageProps<"/parent/books/[bookId]">) {
  const { bookId } = await params;
  const [book, chapters, options] = await Promise.all([getBook(bookId), getChapters(bookId), getOptions()]);
  const reading = book.documents.some(
    (document) => document.status === "queued" || document.status === "processing",
  );

  return (
    <div className="grid max-w-4xl gap-8">
      <AutoRefresh active={reading} />
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">📘 {book.title}</h1>
        <p className="text-muted-foreground">{[book.subject, book.class_label].join(" · ")}</p>
      </div>

      <section className="grid gap-3">
        <h2 className="text-xl font-bold">{text.chaptersTitle}</h2>
        {chapters.length === 0 ? (
          <p className="text-muted-foreground">{text.noChapters}</p>
        ) : (
          <ul className="grid gap-2">
            {chapters.map((chapter) => (
              <li key={chapter.id}>
                <Link
                  href={`/parent/books/${book.id}/chapters/${chapter.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card px-4 py-3 hover:border-primary"
                >
                  <span className="font-semibold">{chapter.label}</span>
                  <span className="text-sm text-muted-foreground">
                    {copy.chapter.exercises}: {chapter.exercise_count} ·{" "}
                    {copy.chapter.questions(chapter.question_count)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-3">
        <h2 className="text-xl font-bold">{text.files}</h2>
        <ul className="grid gap-3">
          {book.documents.map((document) => (
            <li key={document.id} className="grid gap-3 rounded-xl border bg-card p-4 shadow-sm">
              <p className="font-medium break-all">{document.original_filename}</p>
              <DocumentChecklist document={document} />
              {document.status === "ready" && (
                <p className="text-sm text-success">
                  {text.found(
                    document.summary.chapters ?? 0,
                    document.summary.exercises ?? 0,
                    document.summary.questions ?? 0,
                  )}
                </p>
              )}
              <FormMessage message={document.error?.message} />
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
          <BookUploader bookId={book.id} limits={options.upload} />
        </div>
      </section>

      <section className="grid gap-3 rounded-xl border border-destructive/30 p-5">
        <h2 className="text-lg font-bold">{text.deleteBook}</h2>
        <p className="text-sm text-muted-foreground">{text.deleteBookText}</p>
        <ConfirmButton
          label={text.deleteBook}
          confirmLabel={text.deleteConfirm}
          action={deleteBook.bind(null, book.id)}
        />
      </section>
    </div>
  );
}
