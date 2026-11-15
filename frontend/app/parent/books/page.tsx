import Link from "next/link";

import { BookList } from "@/components/book-sections";
import { Button } from "@/components/ui/button";
import { getBooks, getChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.library.title);

/** My Learning Library: every book of the family, labelled with the child it is for. */
export default async function LibraryPage() {
  const copy = await getCopy();
  const text = copy.library;
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
      <BookList books={books} copy={copy} area="parent" detail={(book) => nameOf(book.student_id)} />
    </div>
  );
}
