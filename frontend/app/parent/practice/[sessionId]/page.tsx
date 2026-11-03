import type { Metadata } from "next";

import { AutoRefresh } from "@/components/auto-refresh";
import { FormMessage } from "@/components/form-message";
import { SourceLine } from "@/components/source-line";
import { SubmitButton } from "@/components/submit-button";
import { getPractice, getStudents } from "@/lib/api";
import { startChildMode } from "@/lib/actions/students";
import { copy } from "@/lib/copy";

const text = copy.practice;

export const metadata: Metadata = { title: copy.nav.practice };

/** A practice the parent made: wait while it is prepared, then hand the device to the child. */
export default async function ParentPracticePage({ params }: PageProps<"/parent/practice/[sessionId]">) {
  const { sessionId } = await params;
  const [session, children] = await Promise.all([getPractice(sessionId), getStudents()]);
  const child = children.find((item) => item.id === session.student_id);
  const name = child?.name ?? "";

  return (
    <div className="grid max-w-3xl gap-6">
      <AutoRefresh active={session.status === "preparing"} />
      {session.status === "preparing" && (
        <div role="status" className="grid gap-2 rounded-xl border bg-card p-6 shadow-sm">
          <h1 className="text-2xl font-extrabold">⏳ {text.preparingTitle}</h1>
          <p className="text-muted-foreground">{text.preparingText}</p>
        </div>
      )}
      {session.status === "failed" && (
        <div className="grid gap-3">
          <h1 className="text-2xl font-extrabold">{text.failedTitle}</h1>
          <FormMessage message={session.error?.message} />
        </div>
      )}
      {(session.status === "ready" || session.status === "completed") && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h1 className="text-2xl font-extrabold">✅ {text.readyFor(name)}</h1>
            {session.status === "ready" && (
              <form action={startChildMode.bind(null, session.student_id, session.id)}>
                <SubmitButton size="lg">{text.startNow(name)}</SubmitButton>
              </form>
            )}
          </div>
          <p className="text-muted-foreground">
            {copy.progress.sessionLine(session.answered, session.items.length, session.correct)}
          </p>
          <ol className="grid gap-3">
            {session.items.map(({ question }) => (
              <li key={question.id} className="grid gap-2 rounded-xl border bg-card p-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase">
                  {copy.formats[question.format]} · {copy.difficulties[question.difficulty]}
                </p>
                {question.case && <p className="text-sm text-muted-foreground">{question.case}</p>}
                <p className="font-medium whitespace-pre-line">
                  {question.number}. {question.text}
                </p>
                <SourceLine label={text.generatedFrom} sources={[question.source]} />
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
