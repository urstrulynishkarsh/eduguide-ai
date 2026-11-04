import Link from "next/link";

import type { Copy } from "@/lib/copy";
import type { Progress } from "@/lib/types";
import { cn, formatDay } from "@/lib/utils";

const percent = (value: number) => `${Math.round(value * 100)}%`;

/** How often each area (a chapter, a topic) was right, weakest in the accent colour. */
export function Bars({ title, areas }: { title: string; areas: Progress["by_chapter"] }) {
  if (areas.length === 0) return null;
  return (
    <section className="grid gap-3 rounded-xl border bg-card p-5 shadow-sm">
      <h2 className="text-lg font-bold">{title}</h2>
      <ul className="grid gap-3">
        {areas.map((area) => (
          <li key={area.id} className="grid gap-1">
            <div className="flex justify-between gap-4 text-sm">
              <span className="font-medium">{area.name}</span>
              <span className="text-muted-foreground">
                {percent(area.accuracy)} · {area.attempted}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full", area.accuracy < 0.6 ? "bg-accent" : "bg-success")}
                style={{ width: percent(area.accuracy) }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Basic progress. Nursery – Class 2 (`stars`) never see marks or percentages: a star for every
 * right answer instead (spec §5).
 */
export function ProgressView({
  progress,
  copy,
  stars = false,
  sessionHref,
}: {
  progress: Progress;
  copy: Copy;
  stars?: boolean;
  /** Where a recent session opens; none when the viewer cannot do practice (the parent). */
  sessionHref?: (sessionId: string) => string;
}) {
  const text = copy.progress;
  if (progress.questions_answered === 0 && progress.recent_sessions.length === 0) {
    return <p className="text-muted-foreground">{text.none}</p>;
  }
  if (stars) {
    const count = progress.correct_first_time;
    return (
      <div className="grid justify-items-center gap-4 text-center">
        <p aria-hidden className="text-5xl leading-tight break-all">
          {"⭐".repeat(Math.min(count, 30)) || "🌟"}
        </p>
        <p className="text-3xl font-extrabold">{copy.practice.stars(count)}</p>
        <p className="text-xl text-muted-foreground">{text.keepGoing}</p>
      </div>
    );
  }

  const tiles = [
    [text.answered, String(progress.questions_answered)],
    [text.accuracy, progress.accuracy === null ? "–" : percent(progress.accuracy)],
    [text.time, text.minutes(Math.round(progress.time_spent_ms / 60000))],
    [text.hints, String(progress.hints_used)],
  ];
  return (
    <div className="grid gap-6">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map(([label, value]) => (
          <div key={label} className="grid gap-1 rounded-xl border bg-card p-4 shadow-sm">
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="font-display text-2xl font-extrabold">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-4 md:grid-cols-2">
        <Bars title={text.byChapter} areas={progress.by_chapter} />
        <Bars title={text.byTopic} areas={progress.by_topic} />
      </div>
      {progress.recent_sessions.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold">{text.recent}</h2>
          <ul className="grid gap-2">
            {progress.recent_sessions.map((session) => {
              const line = (
                <>
                  <span className="font-medium">
                    {text.sessionLine(session.answered, session.questions, session.correct)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {text.status[session.status]} ·{" "}
                    {formatDay(copy.language.locale, session.created_at, {
                      day: "numeric",
                      month: "numeric",
                      year: "numeric",
                    })}
                  </span>
                </>
              );
              return (
                <li key={session.id}>
                  {sessionHref ? (
                    <Link
                      href={sessionHref(session.id)}
                      className="flex flex-wrap justify-between gap-2 rounded-lg border bg-card px-4 py-3 hover:border-primary"
                    >
                      {line}
                    </Link>
                  ) : (
                    <div className="flex flex-wrap justify-between gap-2 rounded-lg border bg-card px-4 py-3">
                      {line}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
