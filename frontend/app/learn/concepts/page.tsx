import Link from "next/link";

import { getBooks, getChapters } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.concepts.title);

/** Learn a Concept: the chapters of the learner's books. */
export default async function ConceptsPage() {
  const copy = await getCopy();
  const text = copy.concepts;
  const books = await getBooks();
  const chapters = await Promise.all(books.map((book) => getChapters(book.id)));

  return (
    <div className="grid gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold playful:text-4xl dense:text-2xl">{text.title}</h1>
        <p className="text-muted-foreground">{text.subtitle}</p>
      </div>
      {chapters.flat().length === 0 && <p className="text-muted-foreground">{text.noBooks}</p>}
      {books.map(
        (book, i) =>
          chapters[i].length > 0 && (
            <section key={book.id} className="grid gap-3">
              <h2 className="text-lg font-bold">📘 {book.title}</h2>
              <ul className="grid gap-2 sm:grid-cols-2">
                {chapters[i].map((chapter) => (
                  <li key={chapter.id}>
                    <Link
                      href={`/learn/concepts/${chapter.id}`}
                      className="block rounded-xl border bg-card px-4 py-3 font-semibold hover:border-primary playful:p-6 playful:text-2xl"
                    >
                      💡 {chapter.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ),
      )}
    </div>
  );
}
