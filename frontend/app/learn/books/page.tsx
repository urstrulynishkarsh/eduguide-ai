import { redirect } from "next/navigation";

import { BookList } from "@/components/book-sections";
import { BookUploader } from "@/components/book-uploader";
import { getBooks, getLearner, getOptions } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.library.title);

/**
 * My Books for a student who signed up alone: their books, and Upload Book. A child's books are the
 * parent's to manage (the parent area), so child mode is sent home.
 */
export default async function LearnBooksPage() {
  const copy = await getCopy();
  const { me } = await getLearner();
  if (me.user.role !== "student") redirect("/learn");
  const [books, options] = await Promise.all([getBooks(), getOptions()]);

  return (
    <div className="grid max-w-3xl gap-8">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold dense:text-2xl">{copy.library.title}</h1>
        <p className="text-muted-foreground">{copy.library.mySubtitle}</p>
      </div>
      <BookList books={books} copy={copy} area="learn" />
      <section className="grid gap-4 rounded-xl border bg-card p-5 shadow-sm">
        <div className="grid gap-1">
          <h2 className="text-xl font-bold">{copy.upload.title}</h2>
          <p className="text-sm text-muted-foreground">{copy.upload.subtitle}</p>
        </div>
        <BookUploader area="learn" newBook={{ options }} limits={options.upload} />
      </section>
    </div>
  );
}
