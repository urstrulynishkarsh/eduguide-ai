import type { Metadata } from "next";
import Link from "next/link";

import { AutoRefresh } from "@/components/auto-refresh";
import { FormMessage } from "@/components/form-message";
import { PracticePlayer } from "@/components/practice-player";
import { Button } from "@/components/ui/button";
import { getLearner, getPractice } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.practice;

export const metadata: Metadata = { title: copy.nav.practice };

export default async function PracticeSessionPage({ params }: PageProps<"/learn/practice/[sessionId]">) {
  const { sessionId } = await params;
  const [{ classProfile }, session] = await Promise.all([getLearner(), getPractice(sessionId)]);
  const playful = classProfile.ui_mode === "playful";

  if (session.status === "preparing") {
    return (
      <div role="status" className="mx-auto grid max-w-xl gap-3 py-10 text-center">
        <AutoRefresh active />
        <p aria-hidden className="text-6xl">
          ⏳
        </p>
        <h1 className="text-2xl font-extrabold playful:text-4xl">{text.preparingTitle}</h1>
        <p className="text-muted-foreground">{text.preparingText}</p>
      </div>
    );
  }

  if (session.status === "failed" || session.status === "completed") {
    const failed = session.status === "failed";
    return (
      <div className="mx-auto grid max-w-xl justify-items-center gap-4 py-10 text-center">
        <p aria-hidden className="text-6xl">
          {failed ? "🙈" : "🎉"}
        </p>
        <h1 className="text-3xl font-extrabold playful:text-5xl">
          {failed ? text.failedTitle : playful ? text.playfulDoneTitle : text.doneTitle}
        </h1>
        {failed ? (
          <FormMessage message={session.error?.message} />
        ) : playful ? (
          <p className="text-3xl font-bold">
            {"⭐".repeat(session.correct)} {text.stars(session.correct)}
          </p>
        ) : (
          <p className="text-xl">{text.score(session.correct, session.items.length)}</p>
        )}
        <div className="flex flex-wrap justify-center gap-2">
          <Button asChild size="lg" className="playful:h-16 playful:text-2xl">
            <Link href="/learn/practice">{text.again}</Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="playful:h-16 playful:text-2xl">
            <Link href="/learn">{text.home}</Link>
          </Button>
        </div>
      </div>
    );
  }

  return <PracticePlayer key={session.id} session={session} uiMode={classProfile.ui_mode} />;
}
