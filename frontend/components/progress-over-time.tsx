import { ColumnChart, DataTable, LineChart } from "@/components/charts";
import { Bars } from "@/components/progress-view";
import { testTitle } from "@/components/test-report";
import type { Copy } from "@/lib/copy";
import type { Share, Trends } from "@/lib/types";
import { formatDay } from "@/lib/utils";

const card = "grid content-start gap-3 rounded-xl border bg-card p-5 shadow-sm";

/** Shares as the accuracy bars of Progress, each named in the screen language where it can be. */
const asBars = (shares: Share[], names: Record<string, string> = {}) =>
  shares.map((share) => ({
    id: share.code,
    name: names[share.code] ?? share.code,
    attempted: share.answered,
    accuracy: share.accuracy,
  }));

/**
 * Progress over time ("Track Progress", docs/04 §4.5): the last 12 weeks, test scores, and how well
 * each subject, kind of question and difficulty goes. `simple` (Class 3 – 5): the weeks and the
 * subjects only.
 */
export function ProgressOverTime({
  trends,
  copy,
  simple = false,
}: {
  trends: Trends;
  copy: Copy;
  simple?: boolean;
}) {
  const text = copy.trends;
  const date = (iso: string, options?: Intl.DateTimeFormatOptions) =>
    formatDay(copy.language.locale, iso, options);
  if (trends.weeks.every((week) => week.answered === 0) && trends.tests.length === 0) return null;

  const weeks = trends.weeks.map((week, i) => ({
    key: week.day,
    tick: i % 4 === 0 || i === trends.weeks.length - 1 ? date(week.day) : "",
    label: text.weekOf(date(week.day)),
    answered: week.answered,
    correct: week.correct,
  }));
  const tests = trends.tests.map((test) => ({
    key: test.attempt_id,
    tick: date(test.submitted_at),
    label: `${testTitle(copy, test.kind, test.place)}, ${date(test.submitted_at)}: ${Math.round(test.percentage)}%`,
    value: test.percentage,
  }));

  return (
    <section className="grid gap-4">
      <h2 className="text-xl font-bold">{text.title}</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className={card}>
          <h3 className="text-lg font-bold">{text.weeks}</h3>
          <ColumnChart columns={weeks} label={text.weeks} copy={copy} />
          <DataTable
            summary={text.table}
            head={[text.week, text.answered, copy.dashboard.right, text.minutes]}
            rows={trends.weeks.map((week) => [
              date(week.day),
              String(week.answered),
              String(week.correct),
              String(week.minutes),
            ])}
          />
        </section>
        {!simple && tests.length > 0 && (
          <section className={card}>
            <h3 className="text-lg font-bold">{text.tests}</h3>
            <LineChart points={tests} label={text.tests} />
            <DataTable
              summary={text.table}
              head={[text.test, text.date, text.score]}
              rows={trends.tests.map((test) => [
                testTitle(copy, test.kind, test.place),
                date(test.submitted_at),
                `${test.score} / ${test.total_marks} · ${Math.round(test.percentage)}%`,
              ])}
            />
          </section>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Bars title={text.subjects} areas={asBars(trends.subjects)} />
        {!simple && <Bars title={text.formats} areas={asBars(trends.formats, copy.formats)} />}
        {!simple && <Bars title={text.difficulties} areas={asBars(trends.difficulties, copy.difficulties)} />}
      </div>
    </section>
  );
}
