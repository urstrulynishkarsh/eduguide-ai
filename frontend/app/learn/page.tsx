import { getLearner } from "@/lib/api";
import { copy } from "@/lib/copy";
import { studentNav } from "@/lib/navigation";
import { cn } from "@/lib/utils";

const text = copy.learn;

/** Home. Step 6 adds today's goal, practice and recommendations; for now, the way in. */
export default async function LearnHomePage() {
  const { student, profile, classProfile } = await getLearner();
  const tiles = studentNav(classProfile.ui_mode, classProfile.features).filter(
    (item) => item.href !== "/learn",
  );
  const young = classProfile.ui_mode === "playful" || classProfile.ui_mode === "friendly";

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
          <li
            key={tile.label}
            className={cn(
              "flex items-center gap-4 rounded-xl border bg-card p-5 shadow-sm",
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
            {tile.soon && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground uppercase">
                {copy.soon}
              </span>
            )}
          </li>
        ))}
      </ul>

      <p className="text-muted-foreground playful:text-center playful:text-xl">{text.comingSoon}</p>
    </div>
  );
}
