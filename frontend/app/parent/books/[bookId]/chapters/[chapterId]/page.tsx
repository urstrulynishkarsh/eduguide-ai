import type { Metadata } from "next";
import Link from "next/link";

import { ExplainBox } from "@/components/explain-box";
import { QuickPractice } from "@/components/quick-practice";
import { Button } from "@/components/ui/button";
import { getChapter, getExercise, requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { ExerciseDetail } from "@/lib/types";

const text = copy.chapter;

/**
 * An exercise question as printed. The book's shared instruction ("Solve the following…") is
 * shown once above the list, and the question keeps its own number.
 */
function printedQuestion(question: ExerciseDetail["questions"][number]): string {
  const { instructions, number } = question;
  const rest = (
    instructions && question.text.startsWith(instructions)
      ? question.text.slice(instructions.length)
      : question.text
  ).trim();
  return number && !rest.startsWith(number) ? `${number}. ${rest}` : rest;
}

export const metadata: Metadata = { title: copy.practiceForm.chapter };

/** A chapter: Learn · Practice · Exercise Questions · Generate Questions · Take Test (spec §39). */
export default async function ChapterPage({
  params,
}: PageProps<"/parent/books/[bookId]/chapters/[chapterId]">) {
  const { bookId, chapterId } = await params;
  const [chapter, child] = await Promise.all([getChapter(chapterId), requireChosenChild()]);
  const exercises = await Promise.all(chapter.exercises.map((exercise) => getExercise(exercise.id)));

  return (
    <div className="grid max-w-4xl gap-8">
      <div className="grid gap-1">
        <Link href={`/parent/books/${bookId}`} className="text-sm text-muted-foreground hover:underline">
          ← {copy.library.chaptersTitle}
        </Link>
        <h1 className="text-3xl font-extrabold">{chapter.label}</h1>
      </div>

      <div className="flex flex-wrap items-start gap-2">
        <Button asChild variant="outline">
          <a href="#learn">💡 {text.learn}</a>
        </Button>
        <QuickPractice
          area="parent"
          studentId={child.id}
          chapterId={chapter.id}
          label={`✏️ ${text.practice}`}
        />
        <Button asChild variant="outline">
          <a href="#exercises">📄 {text.exerciseQuestions}</a>
        </Button>
        <Button asChild variant="outline">
          <Link href={`/parent/practice?book=${bookId}&chapter=${chapter.id}`}>✨ {text.generate}</Link>
        </Button>
        <span
          aria-disabled
          className="inline-flex h-9 items-center gap-2 rounded-md border px-4 text-sm text-muted-foreground"
        >
          📝 {text.takeTest}
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase">
            {copy.soon}
          </span>
        </span>
      </div>

      {chapter.topics.length > 0 && (
        <section className="grid gap-2">
          <h2 className="text-xl font-bold">{text.topics}</h2>
          <ul className="flex flex-wrap gap-2">
            {chapter.topics.map((topic) => (
              <li key={topic.id} className="rounded-full border bg-card px-3 py-1 text-sm">
                {[topic.number, topic.title].filter(Boolean).join(" ")}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section id="learn" className="grid scroll-mt-6 gap-3">
        <h2 className="text-xl font-bold">💡 {text.learn}</h2>
        <ExplainBox chapterId={chapter.id} studentId={child.id} />
      </section>

      <section id="exercises" className="grid scroll-mt-6 gap-4">
        <h2 className="text-xl font-bold">📄 {text.exerciseQuestions}</h2>
        {exercises.length === 0 && <p className="text-muted-foreground">{text.noExercises}</p>}
        {exercises.map((exercise) => (
          <article key={exercise.id} className="grid gap-3 rounded-xl border bg-card p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-bold">{exercise.title}</h3>
              <QuickPractice
                area="parent"
                studentId={child.id}
                exerciseId={exercise.id}
                label={`${text.practice}: ${exercise.title}`}
              >
                ✏️ {text.practice}
              </QuickPractice>
            </div>
            <p className="text-xs text-muted-foreground">📘 {text.fromBook}</p>
            {exercise.questions[0]?.instructions && (
              <p className="font-medium">{exercise.questions[0].instructions}</p>
            )}
            <ol className="grid gap-2">
              {exercise.questions.map((question) => (
                <li key={question.id}>
                  <span className="whitespace-pre-line">
                    {printedQuestion(question)}
                    {question.page_start && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        ({text.page(question.page_start)})
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          </article>
        ))}
      </section>
    </div>
  );
}
