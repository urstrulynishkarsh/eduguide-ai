import Link from "next/link";

import { Recommendations } from "@/components/dashboard";
import { TaskActions, TaskLine } from "@/components/plan-view";
import { getDashboard, getLearner, getProgress } from "@/lib/api";
import { copy } from "@/lib/copy";
import { studentNav } from "@/lib/navigation";
import { cn } from "@/lib/utils";

const text = copy.learn;

/** Home: the way in to everything in the learner's menu, Recommended for You, today's plan, practice to continue. */
export default async function LearnHomePage() {
  const { student, profile, classProfile } = await getLearner();
  const [progress, board] = await Promise.all([getProgress(student.id), getDashboard(student.id)]);
  const tiles = studentNav(classProfile.ui_mode, classProfile.features).filter(
    (item) => item.href !== "/learn",
  );
  const young = classProfile.ui_mode === "playful" || classProfile.ui_mode === "friendly";
  const unfinished = progress.recent_sessions.filter((session) => session.status === "ready").slice(0, 3);

  return (
    <div className="grid gap-6 playful:gap-10">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold playful:text-5xl friendly:text-4xl dense:text-2xl">
          {text.hello(student.name)}
        </h1>
        <p className="text-muted-foreground playful:text-2xl friendly:text-xl">
          {classProfile.ui_mode === "playful" ? text.playfulIntro : text.intro}
          <span className="hidden standard:inline dense:inline"> · {profile.class_label}</span>
        </p>
      </div>

      <ul
        className={cn(
          "grid gap-4",
          "playful:grid-cols-1 playful:gap-6 sm:playful:grid-cols-2",
          "friendly:grid-cols-1 sm:friendly:grid-cols-3",
          "sm:standard:grid-cols-2 lg:standard:grid-cols-3",
          "dense:grid-cols-2 dense:gap-3 sm:dense:grid-cols-3 lg:dense:grid-cols-6",
        )}
      >
        {tiles.map((tile) => (
          <li key={tile.label}>
            <Link
              href={tile.href}
              className={cn(
                "flex h-full items-center gap-4 rounded-xl border bg-card p-5 shadow-sm transition hover:border-primary hover:shadow-md",
                "playful:min-h-40 playful:flex-col playful:justify-center playful:rounded-3xl playful:border-4 playful:p-8",
                "friendly:min-h-32 friendly:flex-col friendly:justify-center friendly:border-2",
                "dense:flex-col dense:items-start dense:gap-2 dense:p-4",
              )}
            >
              {young && tile.emoji ? (
                <span aria-hidden className="text-4xl playful:text-7xl">
                  {tile.emoji}
                </span>
              ) : (
                <tile.icon aria-hidden className="size-6 text-primary dense:size-5" />
              )}
              <span className="font-display text-lg font-bold playful:text-3xl friendly:text-2xl dense:text-base">
                {copy.nav[tile.label]}
              </span>
            </Link>
          </li>
        ))}
      </ul>

      {board.recommendations.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold playful:text-2xl">{text.recommended}</h2>
          <Recommendations items={board.recommendations} area="learn" />
        </section>
      )}

      {board.plan && board.plan.today.length > 0 && (
        <section className="grid gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-bold playful:text-2xl">{text.todaysPlan}</h2>
            <Link href="/learn/plan" className="text-sm font-semibold text-primary hover:underline">
              {text.openPlan} →
            </Link>
          </div>
          <ul className="grid gap-2">
            {board.plan.today.map((item) => (
              <TaskLine key={item.id} item={item}>
                <TaskActions item={item} />
              </TaskLine>
            ))}
          </ul>
        </section>
      )}

      {unfinished.length > 0 && (
        <section className="grid gap-3">
          <h2 className="text-lg font-bold playful:text-2xl">{text.recent}</h2>
          <ul className="grid gap-2 sm:grid-cols-3">
            {unfinished.map((session) => (
              <li key={session.id}>
                <Link
                  href={`/learn/practice/${session.id}`}
                  className="flex items-center justify-between gap-2 rounded-xl border bg-card px-4 py-3 font-semibold hover:border-primary"
                >
                  <span>
                    {classProfile.ui_mode === "playful"
                      ? "▶️"
                      : copy.progress.sessionLine(session.answered, session.questions, session.correct)}
                  </span>
                  <span className="text-primary">{text.continue} →</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
