import { AutoSubmitSelect } from "@/components/auto-submit-select";
import { PracticeSettingsForm } from "@/components/practice-settings-form";
import { Label } from "@/components/ui/label";
import { getChapter, getChapters } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { Book, ClassProfile, Option } from "@/lib/types";

const text = copy.practiceForm;
const selectClass =
  "h-9 rounded-md border border-input bg-card px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

interface ChosenPlace {
  book?: string;
  chapter?: string;
  exercise?: string;
}

/**
 * Create Practice. The source is picked step by step (book → chapter → exercise) with a plain GET
 * form, so only the lists in use are loaded; a choice that no longer fits (a chapter of another
 * book) is ignored.
 */
export async function PracticeChooser({
  area,
  studentId,
  books,
  chosen,
  classProfile,
  languages,
  defaultLanguage,
}: {
  area: "parent" | "learn";
  studentId?: string;
  books: Book[];
  chosen: ChosenPlace;
  classProfile: ClassProfile;
  languages: Option[];
  defaultLanguage: string;
}) {
  const book = books.find((item) => item.id === chosen.book);
  const chapters = book ? await getChapters(book.id) : [];
  const chapter = chapters.find((item) => item.id === chosen.chapter);
  const exercises = chapter ? (await getChapter(chapter.id)).exercises : [];
  const exercise = exercises.find((item) => item.id === chosen.exercise);

  const picker = [
    {
      name: "book",
      label: text.book,
      all: text.allBooks,
      value: book?.id,
      items: books.map((b) => [b.id, b.title]),
    },
    book && {
      name: "chapter",
      label: text.chapter,
      all: text.wholeBook,
      value: chapter?.id,
      items: chapters.map((c) => [c.id, c.label]),
    },
    chapter && {
      name: "exercise",
      label: text.exercise,
      all: text.wholeChapter,
      value: exercise?.id,
      items: exercises.map((e) => [e.id, e.title]),
    },
  ].filter(Boolean) as { name: string; label: string; all: string; value?: string; items: string[][] }[];

  return (
    <div className="grid gap-8">
      <form method="get" className="grid gap-3">
        <h2 className="font-display text-lg font-bold">{text.source}</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {picker.map((select) => (
            <div key={select.name} className="grid content-start gap-2">
              <Label htmlFor={`source-${select.name}`}>{select.label}</Label>
              <AutoSubmitSelect
                id={`source-${select.name}`}
                name={select.name}
                defaultValue={select.value ?? ""}
                className={selectClass}
              >
                <option value="">{select.all}</option>
                {select.items.map(([id, title]) => (
                  <option key={id} value={id}>
                    {title}
                  </option>
                ))}
              </AutoSubmitSelect>
            </div>
          ))}
        </div>
      </form>
      <PracticeSettingsForm
        // A new place starts the settings afresh.
        key={[book?.id, chapter?.id, exercise?.id].join()}
        area={area}
        place={{
          student_id: studentId,
          book_id: book?.id,
          chapter_id: chapter?.id,
          exercise_id: exercise?.id,
        }}
        classProfile={classProfile}
        languages={languages}
        defaultLanguage={defaultLanguage}
      />
    </div>
  );
}
