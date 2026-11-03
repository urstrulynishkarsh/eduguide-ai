import type { Metadata } from "next";

import { PracticeChooser } from "@/components/practice-chooser";
import { QuickPractice } from "@/components/quick-practice";
import { getBooks, getChapters, getLearner, getOptions } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.practiceForm;

export const metadata: Metadata = { title: copy.nav.practice };

/**
 * Practice for the learner. Nursery – Class 2 get big "Play" tiles, one per chapter, with the
 * class's usual settings; everyone else gets Create Practice.
 */
export default async function LearnPracticePage({ searchParams }: PageProps<"/learn/practice">) {
  const [{ profile, classProfile }, books, query, options] = await Promise.all([
    getLearner(),
    getBooks(),
    searchParams,
    getOptions(),
  ]);
  if (books.length === 0) return <p className="text-muted-foreground playful:text-2xl">{text.noBooks}</p>;

  if (classProfile.ui_mode === "playful") {
    const chapters = (await Promise.all(books.map((book) => getChapters(book.id)))).flat();
    const tile =
      "h-auto min-h-36 w-full flex-col gap-2 rounded-3xl border-4 border-border bg-card p-6 text-2xl font-bold text-foreground shadow-sm hover:bg-secondary";
    return (
      <div className="grid gap-6">
        <h1 className="text-4xl font-extrabold">{text.playfulTitle}</h1>
        <div className="grid gap-6 sm:grid-cols-2">
          <QuickPractice area="learn" label={text.playfulAll} className={tile}>
            <span aria-hidden className="text-6xl">
              🎈
            </span>
            {text.playfulAll}
          </QuickPractice>
          {chapters.map((chapter) => (
            <QuickPractice
              key={chapter.id}
              area="learn"
              chapterId={chapter.id}
              label={chapter.label}
              className={tile}
            >
              <span aria-hidden className="text-6xl">
                ⭐
              </span>
              <span className="text-center whitespace-normal">{chapter.label}</span>
            </QuickPractice>
          ))}
        </div>
      </div>
    );
  }

  const pick = (name: string) => (typeof query[name] === "string" ? (query[name] as string) : undefined);
  return (
    <div className="grid max-w-3xl gap-6">
      <h1 className="text-3xl font-extrabold dense:text-2xl">{text.title}</h1>
      <PracticeChooser
        area="learn"
        books={books}
        chosen={{ book: pick("book"), chapter: pick("chapter"), exercise: pick("exercise") }}
        classProfile={classProfile}
        languages={options.languages}
        defaultLanguage={profile.primary_language}
      />
    </div>
  );
}
