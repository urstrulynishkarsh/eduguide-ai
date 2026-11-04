import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { BookUploader } from "@/components/book-uploader";
import { ConfirmButton } from "@/components/confirm-button";
import { DocumentChecklist } from "@/components/document-checklist";
import { FormMessage } from "@/components/form-message";
import { PaperAnalysisView } from "@/components/paper-analysis";
import { SubmitButton } from "@/components/submit-button";
import {
  getBook,
  getChapters,
  getChosenChild,
  getClassProfile,
  getOptions,
  getPaperAnalysis,
} from "@/lib/api";
import { deleteBook, removeDocument, retryDocument } from "@/lib/actions/books";
import { copy } from "@/lib/copy";
import type { Book } from "@/lib/types";

const text = copy.library;

export const metadata: Metadata = { title: text.title };

/** A book: its chapters and files; for previous-year papers (Class 9–12), their analysis too. */
export default async function BookPage({ params }: PageProps<"/parent/books/[bookId]">) {
  const { bookId } = await params;
  const [book, chapters, options] = await Promise.all([getBook(bookId), getChapters(bookId), getOptions()]);
  const reading = book.documents.some(
    (document) => document.status === "queued" || document.status === "processing",
  );
  // A book of previous-year papers: each file is a paper, made of sections.
  const isPapers = book.material_type === "previous_year_paper";
  const papers = isPapers && (await paperAnalysis(book));

  return (
    <div className="grid max-w-4xl gap-8">
      <AutoRefresh active={reading} />
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">📘 {book.title}</h1>
        <p className="text-muted-foreground">{[book.subject, book.class_label].join(" · ")}</p>
      </div>

      <section className="grid gap-3">
        <h2 className="text-xl font-bold">{isPapers ? text.papersTitle : text.chaptersTitle}</h2>
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
                    {isPapers ? copy.chapter.sections : copy.chapter.exercises}: {chapter.exercise_count} ·{" "}
                    {copy.chapter.questions(chapter.question_count)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {papers && (
        <PaperAnalysisView
          bookId={book.id}
          analysis={papers.analysis}
          studentId={papers.studentId}
          classLabel={book.class_label}
        />
      )}

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

/**
 * The analysis of a book of papers, where its class has previous-year papers, and the child who may
 * practise them: the one the book is for, or else the chosen child - when in the papers' class.
 */
async function paperAnalysis(book: Book) {
  const [classProfile, { children, child }] = await Promise.all([
    getClassProfile(book.class_level),
    getChosenChild(),
  ]);
  if (!classProfile.features.previous_year_questions) return null;
  const learner = children.find((item) => item.id === book.student_id) ?? child;
  return {
    analysis: await getPaperAnalysis(book.id),
    studentId: learner?.profile?.class_level === book.class_level ? learner.id : null,
  };
}
