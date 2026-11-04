import { AutoRefresh } from "@/components/auto-refresh";
import { Sparkline } from "@/components/charts";
import { FormMessage } from "@/components/form-message";
import { StartButton } from "@/components/start-button";
import { analysePapers } from "@/lib/actions/books";
import { createPractice } from "@/lib/actions/practice";
import { createTest } from "@/lib/actions/tests";
import type { Copy } from "@/lib/copy";
import type { PaperAnalysis } from "@/lib/types";

const card = "grid content-start gap-3 rounded-xl border bg-card p-5 shadow-sm";
const percent = (share: number) => `${Math.round(share * 100)}%`;

/**
 * The analysis of a book of previous-year papers: each paper, where the marks go (the textbook
 * chapters by their marks in a paper, in how many papers, rising or falling), the topics asked most,
 * the kinds of questions and the latest paper's layout. A chapter can be practised, and a test like
 * the papers made, for `studentId` - a child of the papers' class (none: the parent is told).
 */
export function PaperAnalysisView({
  bookId,
  analysis,
  studentId,
  classLabel,
  copy,
}: {
  bookId: string;
  analysis: PaperAnalysis;
  studentId: string | null;
  classLabel: string;
  copy: Copy;
}) {
  const text = copy.papers;
  const preparing = analysis.status === "preparing";
  const forChild = (fields: Record<string, string | number | null>) => ({ ...fields, student_id: studentId });

  return (
    <section className="grid gap-4">
      <AutoRefresh active={preparing} />
      <div className="grid gap-1">
        <h2 className="text-xl font-bold">{text.title}</h2>
        <p className="text-muted-foreground">{text.intro}</p>
      </div>
      <ul className="grid gap-2">
        {analysis.papers.map((paper) => (
          <li
            key={paper.document_id}
            className="flex flex-wrap justify-between gap-2 rounded-lg border bg-card px-4 py-3"
          >
            <span className="font-semibold">{paper.title}</span>
            <span className="text-sm text-muted-foreground">
              {paper.status === "ready"
                ? text.paperLine(paper.year, paper.questions, paper.total_marks)
                : paper.status === "preparing"
                  ? copy.loading
                  : text.notYet}
            </span>
            <FormMessage error={paper.error} />
          </li>
        ))}
      </ul>
      {preparing ? (
        <p role="status" className="text-muted-foreground">
          ⏳ {text.preparing}
        </p>
      ) : (
        <div className="grid justify-items-start gap-1">
          <StartButton
            action={analysePapers.bind(null, bookId)}
            fields={{}}
            label={analysis.status === "none" ? text.analyse : text.analyseAgain}
            variant={analysis.status === "none" ? "default" : "outline"}
          />
          {analysis.status !== "none" && (
            <p className="text-sm text-muted-foreground">{text.analyseAgainHint}</p>
          )}
        </div>
      )}
      {analysis.status === "failed" && <FormMessage message={text.failed} />}

      {analysis.papers.some((paper) => paper.status === "ready") && (
        <>
          {!studentId && <p className="text-muted-foreground">{text.otherClass(classLabel)}</p>}
          <section className={card}>
            <h3 className="text-lg font-bold">{text.whereMarks}</h3>
            {analysis.chapters.length === 0 && <p className="text-muted-foreground">{text.noTextbook}</p>}
            <ul className="grid gap-4">
              {analysis.chapters.map((chapter) => (
                <li key={chapter.chapter_id} className="flex flex-wrap items-center justify-between gap-3">
                  <div className="grid min-w-56 flex-1 gap-1">
                    <div className="flex flex-wrap items-center justify-between gap-x-4 text-sm">
                      <span className="font-medium">{chapter.chapter}</span>
                      <span className="flex items-center gap-2 text-muted-foreground">
                        {text.marksLine(chapter.marks_per_paper, chapter.papers, analysis.papers.length)}
                        {chapter.trend && ` · ${text.trend[chapter.trend]}`}
                        {chapter.by_year.length > 1 && (
                          <Sparkline
                            values={chapter.by_year.map((year) => year.marks)}
                            label={copy.trends.byYear(
                              chapter.by_year.map(({ year, marks }) => `${year}: ${marks}`).join(", "),
                            )}
                          />
                        )}
                      </span>
                    </div>
                    <div
                      role="img"
                      aria-label={percent(chapter.share)}
                      className="h-2 overflow-hidden rounded-full bg-muted"
                    >
                      <div className="h-full bg-primary" style={{ width: percent(chapter.share) }} />
                    </div>
                  </div>
                  {studentId && (
                    <StartButton
                      action={createPractice.bind(null, "parent")}
                      fields={forChild(chapter.practice)}
                      label={`${text.practise}: ${chapter.chapter}`}
                      variant="outline"
                    >
                      {text.practise}
                    </StartButton>
                  )}
                </li>
              ))}
            </ul>
            {analysis.unmatched.questions > 0 && analysis.chapters.length > 0 && (
              <p className="text-sm text-muted-foreground">{text.unmatched(analysis.unmatched.questions)}</p>
            )}
          </section>

          <div className="grid gap-4 md:grid-cols-3">
            {analysis.topics.length > 0 && (
              <section className={card}>
                <h3 className="text-lg font-bold">{text.topics}</h3>
                <ul className="grid gap-2 text-sm">
                  {analysis.topics.map((topic) => (
                    <li key={`${topic.chapter_id}${topic.topic}`} className="grid">
                      <span className="font-medium">{topic.topic}</span>
                      <span className="text-muted-foreground">
                        {text.topicLine(topic.questions, topic.papers)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section className={card}>
              <h3 className="text-lg font-bold">{text.kinds}</h3>
              <ul className="grid gap-2 text-sm">
                {analysis.formats.map((kind) => (
                  <li key={kind.format} className="flex justify-between gap-4">
                    <span>{copy.formats[kind.format] ?? kind.format}</span>
                    <span className="text-muted-foreground tabular-nums">{percent(kind.share)}</span>
                  </li>
                ))}
              </ul>
            </section>
            <section className={card}>
              <h3 className="text-lg font-bold">{text.layout(analysis.layout_year)}</h3>
              <ul className="grid gap-2 text-sm">
                {analysis.layout.map((section) => (
                  <li key={section.title} className="grid">
                    <span className="font-medium">{section.title}</span>
                    <span className="text-muted-foreground">
                      {text.layoutLine(section.questions, section.marks)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          {analysis.test && studentId && (
            <StartButton
              action={createTest.bind(null, "parent")}
              fields={forChild(analysis.test)}
              label={text.makeTest}
              className="justify-self-start"
            />
          )}
        </>
      )}
    </section>
  );
}
