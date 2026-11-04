import { AutoSubmitSelect } from "@/components/auto-submit-select";
import { QuestionSettingsForm } from "@/components/question-settings-form";
import { Label } from "@/components/ui/label";
import { getChapter, getChapters } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { Book, ClassFeatures, ClassProfile, Exam, Option, TestKind } from "@/lib/types";
import { searchParam } from "@/lib/utils";

const text = copy.practiceForm;
const selectClass =
  "h-9 rounded-md border border-input bg-card px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

/** What the GET form of the page has chosen so far (`?kind=&book=&chapter=&exercise=`). */
export interface Chosen {
  kind?: string;
  book?: string;
  chapter?: string;
  exercise?: string;
}

/** The choices so far, from the page's search params. */
export function chosenFrom(query: Record<string, string | string[] | undefined>): Chosen {
  const [kind, book, chapter, exercise] = ["kind", "book", "chapter", "exercise"].map((name) =>
    searchParam(query, name),
  );
  return { kind, book, chapter, exercise };
}

interface Select {
  name: string;
  label: string;
  /** The first option, meaning "all of them"; none when one must be chosen. */
  all?: string;
  value?: string;
  items: string[][];
}

/**
 * The place, picked step by step (book → chapter → exercise, `depth` levels deep) with a plain GET
 * form, so only the lists in use are loaded. A choice that no longer fits (a chapter of another
 * book) is ignored.
 */
async function pickPlace(books: Book[], chosen: Chosen, depth: number) {
  const book = books.find((item) => item.id === chosen.book);
  const chapters = book && depth > 1 ? await getChapters(book.id) : [];
  const chapter = chapters.find((item) => item.id === chosen.chapter);
  const exercises = chapter && depth > 2 ? (await getChapter(chapter.id)).exercises : [];
  const exercise = exercises.find((item) => item.id === chosen.exercise);

  const selects: Select[] = [
    {
      name: "book",
      label: text.book,
      all: text.allBooks,
      value: book?.id,
      items: books.map((b) => [b.id, b.title]),
    },
  ];
  if (book && depth > 1) {
    selects.push({
      name: "chapter",
      label: text.chapter,
      all: text.wholeBook,
      value: chapter?.id,
      items: chapters.map((c) => [c.id, c.label]),
    });
  }
  if (chapter && depth > 2) {
    selects.push({
      name: "exercise",
      label: text.exercise,
      all: text.wholeChapter,
      value: exercise?.id,
      items: exercises.map((e) => [e.id, e.title]),
    });
  }
  return { place: { book_id: book?.id, chapter_id: chapter?.id, exercise_id: exercise?.id }, selects };
}

function Picker({ title, selects }: { title?: string; selects: Select[] }) {
  return (
    <form method="get" className="grid gap-3">
      {title && <h2 className="font-display text-lg font-bold">{title}</h2>}
      <div className="grid gap-4 sm:grid-cols-3">
        {selects.map((select) => (
          <div key={select.name} className="grid content-start gap-2">
            <Label htmlFor={`source-${select.name}`}>{select.label}</Label>
            <AutoSubmitSelect
              id={`source-${select.name}`}
              name={select.name}
              defaultValue={select.value ?? ""}
              className={selectClass}
            >
              {select.all && <option value="">{select.all}</option>}
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
  );
}

interface ChooserProps {
  area: "parent" | "learn";
  studentId?: string;
  books: Book[];
  chosen: Chosen;
  classProfile: ClassProfile;
  languages: Option[];
  defaultLanguage: string;
}

/** Create Practice: the source (book → chapter → exercise), then the settings. */
export async function PracticeChooser({ area, studentId, books, chosen, ...settings }: ChooserProps) {
  const { place, selects } = await pickPlace(books, chosen, 3);
  return (
    <div className="grid gap-8">
      <Picker title={text.source} selects={selects} />
      <QuestionSettingsForm
        // A new place starts the settings afresh.
        key={Object.values(place).join()}
        area={area}
        place={{ student_id: studentId, ...place }}
        {...settings}
      />
    </div>
  );
}

// A previous-year pattern test is made from its book's paper analysis, not here.
type ChosenKind = Exclude<TestKind, "previous_year">;
const KIND_FEATURE: Record<ChosenKind, keyof ClassFeatures> = {
  practice: "practice_tests",
  chapter: "chapter_tests",
  full_mock: "full_mock_tests",
};
const EXAMS = new Set<string>(["jee", "neet", "cuet"] satisfies Exam[]);

/**
 * Create Test: the kinds the class has, the place the kind allows (a full mock covers a book or all
 * books; a chapter test needs a chapter), then the settings. A learner whose goal is JEE, NEET or
 * CUET (Class 11–12) is told their tests follow the exam's pattern.
 */
export async function TestChooser({
  area,
  studentId,
  books,
  chosen,
  goal,
  ...settings
}: ChooserProps & { goal: string }) {
  const kinds = (Object.keys(KIND_FEATURE) as ChosenKind[]).filter(
    (kind) => settings.classProfile.features[KIND_FEATURE[kind]],
  );
  if (kinds.length === 0) return <p className="text-muted-foreground">{copy.tests.notForClass}</p>;
  const exam = settings.classProfile.features.competitive_exam_modes && EXAMS.has(goal) ? goal : null;
  const kind = kinds.find((item) => item === chosen.kind) ?? kinds[0];
  const { place, selects } = await pickPlace(books, chosen, kind === "full_mock" ? 1 : 2);
  const kindSelect = {
    name: "kind",
    label: copy.tests.kind,
    value: kind,
    items: kinds.map((item) => [item, copy.testKinds[item]]),
  };

  return (
    <div className="grid gap-8">
      {exam && (
        <p className="rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm">
          {copy.tests.examMode(copy.exams[exam])}
        </p>
      )}
      <Picker selects={[kindSelect, ...selects]} />
      <QuestionSettingsForm
        key={[kind, ...Object.values(place)].join()}
        area={area}
        place={{ student_id: studentId, ...place }}
        test={kind}
        {...settings}
      />
    </div>
  );
}
