import { AutoRefresh } from "@/components/auto-refresh";
import { BookChapters, BookFiles, DeleteBook, isReading } from "@/components/book-sections";
import { PaperAnalysisView } from "@/components/paper-analysis";
import {
  getBook,
  getBookLearner,
  getChapters,
  getClassProfile,
  getOptions,
  getPaperAnalysis,
} from "@/lib/api";
import { classLabel } from "@/lib/copy";
import { getCopy, titled } from "@/lib/copy/server";
import type { Book } from "@/lib/types";

export const generateMetadata = titled((copy) => copy.library.title);

/** A book: its chapters and files; for previous-year papers (Class 9–12), their analysis too. */
export default async function BookPage({ params }: PageProps<"/parent/books/[bookId]">) {
  const copy = await getCopy();
  const { bookId } = await params;
  const [book, chapters, options] = await Promise.all([getBook(bookId), getChapters(bookId), getOptions()]);
  // A book of previous-year papers: each file is a paper, made of sections.
  const isPapers = book.material_type === "previous_year_paper";
  const papers = isPapers && (await paperAnalysis(book));

  return (
    <div className="grid max-w-4xl gap-8">
      <AutoRefresh active={isReading(book)} />
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">📘 {book.title}</h1>
        <p className="text-muted-foreground">{[book.subject, classLabel(copy, book)].join(" · ")}</p>
      </div>
      <BookChapters
        chapters={chapters}
        copy={copy}
        isPapers={isPapers}
        href={(chapter) => `/parent/books/${book.id}/chapters/${chapter.id}`}
      />
      {papers && (
        <PaperAnalysisView
          copy={copy}
          bookId={book.id}
          analysis={papers.analysis}
          studentId={papers.studentId}
          classLabel={classLabel(copy, book)}
        />
      )}
      <BookFiles book={book} copy={copy} area="parent" limits={options.upload} />
      <DeleteBook book={book} copy={copy} area="parent" />
    </div>
  );
}

/**
 * The analysis of a book of papers, where its class has previous-year papers, and the child who may
 * practise them: the one the book is for, or else the chosen child - when in the papers' class.
 */
async function paperAnalysis(book: Book) {
  const [classProfile, learner] = await Promise.all([
    getClassProfile(book.class_level),
    getBookLearner(book),
  ]);
  if (!classProfile.features.previous_year_questions) return null;
  return {
    analysis: await getPaperAnalysis(book.id),
    studentId: learner?.profile?.class_level === book.class_level ? learner.id : null,
  };
}
