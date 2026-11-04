import { chosenFrom, TestChooser } from "@/components/question-chooser";
import { getBooks, getClassProfile, getOptions, requireChosenChild } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.tests.create);

/** Create Test for the chosen child. `?kind=&book=&chapter=` preselect it. */
export default async function NewTestPage({ searchParams }: PageProps<"/parent/tests/new">) {
  const copy = await getCopy();
  const child = await requireChosenChild();
  const profile = child.profile!;
  const [query, options, books, classProfile] = await Promise.all([
    searchParams,
    getOptions(),
    getBooks(child.id),
    getClassProfile(profile.class_level),
  ]);

  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.tests.create}</h1>
        <p className="text-muted-foreground">{copy.tests.subtitle(child.name)}</p>
      </div>
      <TestChooser
        area="parent"
        studentId={child.id}
        books={books}
        chosen={chosenFrom(query)}
        goal={profile.goal}
        classProfile={classProfile}
        languages={options.languages}
        defaultLanguage={profile.primary_language}
      />
    </div>
  );
}
