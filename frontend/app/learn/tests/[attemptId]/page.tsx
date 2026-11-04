import Link from "next/link";

import { TestPlayer } from "@/components/test-player";
import { placeOf, TestReportView, testTitle } from "@/components/test-report";
import { getAttempt, getReport, getTest } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.tests.myTitle);

/** A sitting: the test while it is being taken (after a reload too), then its report. */
export default async function TestAttemptPage({ params }: PageProps<"/learn/tests/[attemptId]">) {
  const copy = await getCopy();
  const text = copy.tests;
  const { attemptId } = await params;
  const attempt = await getAttempt(attemptId);
  const test = await getTest(attempt.mock_test_id);
  const title = testTitle(copy, test.kind, placeOf(test));
  if (attempt.status === "in_progress")
    return <TestPlayer key={attempt.id} attempt={attempt} title={title} />;

  const report = await getReport(attemptId);
  return (
    <div className="grid max-w-4xl gap-6">
      <div className="grid gap-1">
        <Link href="/learn/tests" className="text-sm text-muted-foreground hover:underline">
          ← {text.allTests}
        </Link>
        <h1 className="text-3xl font-extrabold dense:text-2xl">
          {text.reportTitle}: {title}
        </h1>
      </div>
      <TestReportView copy={copy} report={report} />
    </div>
  );
}
