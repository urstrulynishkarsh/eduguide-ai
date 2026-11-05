import { RecentPractice } from "@/components/progress-view";
import { chosenFrom, PracticeChooser } from "@/components/question-chooser";
import { StartButton } from "@/components/start-button";
import { createPractice } from "@/lib/actions/practice";
import { getBooks, getChapters, getLearner, getOptions, getProgress } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.nav.practice);

/**
 * Practice for the learner. Nursery – Class 2 get big "Play" tiles, one per chapter, with the
 * class's usual settings; everyone else gets Create Practice, under their latest practices (one left
 * while being prepared or half done opens again from there).
 */
export default async function LearnPracticePage({ searchParams }: PageProps<"/learn/practice">) {
  const copy = await getCopy();
  const text = copy.practiceForm;
  const [{ student, profile, classProfile }, books, query, options] = await Promise.all([
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
          <StartButton
            action={createPractice.bind(null, "learn")}
            fields={{}}
            label={text.playfulAll}
            className={tile}
          >
            <span aria-hidden className="text-6xl">
              🎈
            </span>
            {text.playfulAll}
          </StartButton>
          {chapters.map((chapter) => (
            <StartButton
              key={chapter.id}
              action={createPractice.bind(null, "learn")}
              fields={{ chapter_id: chapter.id }}
              label={chapter.label}
              className={tile}
            >
              <span aria-hidden className="text-6xl">
                ⭐
              </span>
              <span className="text-center whitespace-normal">{chapter.label}</span>
            </StartButton>
          ))}
        </div>
      </div>
    );
  }

  const progress = await getProgress(student.id);
  return (
    <div className="grid max-w-3xl gap-6">
      <h1 className="text-3xl font-extrabold dense:text-2xl">{text.title}</h1>
      <RecentPractice sessions={progress.recent_sessions} copy={copy} area="learn" />
      <PracticeChooser
        area="learn"
        books={books}
        chosen={chosenFrom(query)}
        classProfile={classProfile}
        languages={options.languages}
        defaultLanguage={profile.primary_language}
      />
    </div>
  );
}
