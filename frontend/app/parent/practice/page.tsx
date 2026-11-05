import { RecentPractice } from "@/components/progress-view";
import { chosenFrom, PracticeChooser } from "@/components/question-chooser";
import { getBooks, getClassProfile, getOptions, getProgress, requireChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.practiceForm.title);

/**
 * Create Practice for the chosen child, under their latest practices (one left while being prepared
 * opens again from there). `?book=&chapter=&exercise=` preselect the source.
 */
export default async function CreatePracticePage({ searchParams }: PageProps<"/parent/practice">) {
  const copy = await getCopy();
  const child = await requireChosenChild();
  const [query, options, books, progress] = await Promise.all([
    searchParams,
    getOptions(),
    getBooks(child.id),
    getProgress(child.id),
  ]);
  const profile = child.profile!;
  const classProfile = await getClassProfile(profile.class_level);

  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.practiceForm.title}</h1>
        <p className="text-muted-foreground">{copy.practiceForm.subtitle(child.name)}</p>
      </div>
      <RecentPractice sessions={progress.recent_sessions} copy={copy} area="parent" />
      <PracticeChooser
        area="parent"
        studentId={child.id}
        books={books}
        chosen={chosenFrom(query)}
        classProfile={classProfile}
        languages={options.languages}
        defaultLanguage={profile.primary_language}
      />
    </div>
  );
}
