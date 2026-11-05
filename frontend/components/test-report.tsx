import { Bars } from "@/components/progress-view";
import type { Copy } from "@/lib/copy";
import type { Answer, MockTest, Question, TestKind, TestReport } from "@/lib/types";
import { cn } from "@/lib/utils";

/** "Chapter test · Chapter 4 Simple Equations"; a test without a place covers all books. */
export function testTitle(copy: Copy, kind: TestKind, place: string | null): string {
  return `${copy.testKinds[kind]} · ${place ?? copy.tests.allBooks}`;
}

/** The most specific place of a test: its exercise, topic, chapter or book. */
export const placeOf = (test: MockTest) => test.exercise ?? test.topic ?? test.chapter ?? test.book_title;

/** Its size and time, and the exam whose pattern it follows (JEE / NEET / CUET mode). */
export const testSummary = (copy: Copy, test: MockTest) =>
  [
    copy.tests.summary(test.question_count, test.total_marks, test.duration_minutes),
    test.exam && copy.exams[test.exam],
  ]
    .filter(Boolean)
    .join(" · ");

/** A test in a list: its name and size. */
export function TestHeading({ test, copy }: { test: MockTest; copy: Copy }) {
  return (
    <div className="grid gap-1">
      <p className="font-semibold">{testTitle(copy, test.kind, placeOf(test))}</p>
      <p className="text-sm text-muted-foreground">{testSummary(copy, test)}</p>
    </div>
  );
}

/** The learner's answer in words: a matching question's pairs as "left → right". */
function answerText(question: Question, answer: Answer): string {
  if (answer.option != null) return question.options[answer.option];
  if (answer.value != null) return [answer.value, question.unit].filter(Boolean).join(" ");
  if (answer.pairs) {
    return answer.pairs
      .map((right, left) => `${question.match_left[left]} → ${question.match_right[right]}`)
      .join(", ");
  }
  return answer.text ?? "";
}

/**
 * The result report: the score, each section, the chapters and topics weakest first, and every
 * question with the answer given, its marks and the worked solution.
 */
export function TestReportView({ report, copy }: { report: TestReport; copy: Copy }) {
  const text = copy.tests;
  const tiles = [
    [text.score, `${report.score} / ${report.total_marks}`, `${Math.round(report.percentage)}%`],
    [text.correct, String(report.correct)],
    [text.wrong, String(report.wrong)],
    [text.notAnswered, String(report.unanswered)],
    [text.timeTaken, copy.progress.minutes(Math.round(report.time_taken_ms / 60000))],
  ];
  return (
    <div className="grid gap-6">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {tiles.map(([label, value, share]) => (
          <div key={label} className="grid gap-1 rounded-xl border bg-card p-4 shadow-sm">
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="font-display text-2xl font-extrabold">
              {value} {share && <span className="text-base text-muted-foreground">{share}</span>}
            </dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="grid content-start gap-3 rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="text-lg font-bold">{text.bySection}</h2>
          <ul className="grid gap-2 text-sm">
            {report.sections.map((section) => (
              <li key={section.code} className="flex justify-between gap-4">
                <span className="font-medium">
                  {section.code} · {section.title}
                </span>
                <span className="text-muted-foreground tabular-nums">
                  {section.score} / {section.total_marks}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <Bars
          title={text.byArea}
          areas={report.areas.map((area) => ({
            id: `${area.chapter_id}${area.topic}`,
            name: area.topic ?? area.chapter,
            attempted: area.questions,
            accuracy: area.accuracy,
          }))}
        />
      </div>

      <section className="grid gap-3">
        <h2 className="text-lg font-bold">{text.questions}</h2>
        <ol className="grid gap-3">
          {report.questions.map(
            ({ question, marks, marks_awarded, correct, response, feedback, solution }) => (
              <li key={question.id} className="grid gap-2 rounded-xl border bg-card p-4">
                <div className="flex justify-between gap-4">
                  <p className="font-medium whitespace-pre-line">
                    {question.number}. {question.text}
                  </p>
                  <span
                    className={cn(
                      "shrink-0 font-semibold tabular-nums",
                      correct ? "text-success" : "text-muted-foreground",
                      (marks_awarded ?? 0) < 0 && "text-destructive",
                    )}
                  >
                    {text.marks(marks_awarded, marks)}
                  </span>
                </div>
                <p className="text-sm">
                  {response ? (
                    `${text.yourAnswer} ${answerText(question, response)}`
                  ) : (
                    <span className="text-muted-foreground">{text.notAnswered}</span>
                  )}
                </p>
                {feedback && <p className="text-sm text-muted-foreground">{feedback}</p>}
                <details className="text-sm">
                  <summary className="cursor-pointer font-semibold text-primary">{text.solution}</summary>
                  <div className="mt-2 grid gap-2">
                    <p>
                      <strong>{copy.practice.concept}:</strong> {solution.concept}
                    </p>
                    {solution.steps.length > 0 && (
                      <ol className="grid list-decimal gap-1 pl-5">
                        {solution.steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    )}
                    <p>
                      <strong>{copy.practice.finalAnswer}:</strong> {solution.final_answer}
                    </p>
                  </div>
                </details>
              </li>
            ),
          )}
        </ol>
      </section>
    </div>
  );
}
