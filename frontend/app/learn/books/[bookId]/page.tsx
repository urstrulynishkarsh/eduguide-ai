import Link from "next/link";
import { redirect } from "next/navigation";

import { AutoRefresh } from "@/components/auto-refresh";
import { BookChapters, BookFiles, DeleteBook, isReading } from "@/components/book-sections";
import { getBook, getChapters, getLearner, getOptions } from "@/lib/api";
import { classLabel } from "@/lib/copy";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.library.title);

/** A solo student's book: its chapters (each opening Learn a Concept) and its files. */
export default async function LearnBookPage({ params }: PageProps<"/learn/books/[bookId]">) {
  const copy = await getCopy();
  const [{ bookId }, { me }] = await Promise.all([params, getLearner()]);
  if (me.user.role !== "student") redirect("/learn");
  const [book, chapters, options] = await Promise.all([getBook(bookId), getChapters(bookId), getOptions()]);

  return (
    <div className="grid max-w-3xl gap-8">
      <AutoRefresh active={isReading(book)} />
      <div className="grid gap-1">
        <Link href="/learn/books" className="text-sm text-muted-foreground hover:underline">
          ← {copy.library.title}
        </Link>
        <h1 className="text-3xl font-extrabold dense:text-2xl">📘 {book.title}</h1>
        <p className="text-muted-foreground">{[book.subject, classLabel(copy, book)].join(" · ")}</p>
      </div>
      <BookChapters
        chapters={chapters}
        copy={copy}
        isPapers={book.material_type === "previous_year_paper"}
        href={(chapter) => `/learn/concepts/${chapter.id}`}
      />
      <BookFiles book={book} copy={copy} area="learn" limits={options.upload} />
      <DeleteBook book={book} copy={copy} area="learn" />
    </div>
  );
}
