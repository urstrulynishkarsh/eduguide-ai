import type { Metadata } from "next";

import { PracticeChooser } from "@/components/practice-chooser";
import { getBooks, getClassProfile, getOptions, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.practiceForm.title };

/** Create Practice for the chosen child. `?book=&chapter=&exercise=` preselect the source. */
export default async function CreatePracticePage({ searchParams }: PageProps<"/parent/practice">) {
  const child = await requireChosenChild();
  const [query, options, books] = await Promise.all([searchParams, getOptions(), getBooks(child.id)]);
  const profile = child.profile!;
  const classProfile = await getClassProfile(profile.class_level);
  const pick = (name: string) => (typeof query[name] === "string" ? (query[name] as string) : undefined);

  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.practiceForm.title}</h1>
        <p className="text-muted-foreground">{copy.practiceForm.subtitle(child.name)}</p>
      </div>
      <PracticeChooser
        area="parent"
        studentId={child.id}
        books={books}
        chosen={{ book: pick("book"), chapter: pick("chapter"), exercise: pick("exercise") }}
        classProfile={classProfile}
        languages={options.languages}
        defaultLanguage={profile.primary_language}
      />
    </div>
  );
}
