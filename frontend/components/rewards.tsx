import type { Copy } from "@/lib/copy";
import type { Rewards } from "@/lib/types";
import { cn, formatDay } from "@/lib/utils";

/** A badge's picture; the words are in lib/copy (`rewards.badges`). */
export const BADGE_EMOJI: Record<string, string> = {
  first_practice: "🚀",
  perfect_practice: "💯",
  right_10: "⭐",
  right_100: "🌟",
  streak_3: "🔥",
  streak_7: "📅",
  streak_30: "🏆",
  first_test: "📝",
  topic_mastered: "🧠",
  mistake_fixed: "🔧",
  level_5: "🎖️",
};

/** A badge's name; a badge this screen doesn't know yet (a newer backend) by its code. */
export const badgeName = (copy: Copy, code: string) => copy.rewards.badges[code]?.name ?? code;

function Meter({ share, label }: { share: number; label: string }) {
  const percent = Math.round(Math.min(share, 1) * 100);
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-2 overflow-hidden rounded-full bg-muted playful:h-4"
    >
      <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
    </div>
  );
}

/**
 * The streak, the level with its XP, and today's goal. Nursery – Class 2 (`playful`) see no XP or
 * levels: the streak and today's goal only.
 */
export function RewardStrip({
  rewards,
  copy,
  playful = false,
}: {
  rewards: Rewards;
  copy: Copy;
  playful?: boolean;
}) {
  const text = copy.rewards;
  const { answered, goal } = rewards.today;
  const goalLine = answered >= goal ? text.goalDone : text.today(answered, goal);
  return (
    <div
      className={cn(
        "grid gap-4 rounded-xl border bg-card p-4 shadow-sm sm:grid-cols-[1fr_1fr_1fr]",
        "playful:rounded-3xl playful:border-4 playful:p-6 playful:text-xl sm:playful:grid-cols-2",
      )}
    >
      <div className="grid content-start gap-1">
        <p className="font-display text-lg font-bold playful:text-2xl">{text.streak(rewards.streak)}</p>
        {answered === 0 && (
          <p className="text-sm text-muted-foreground playful:text-base">{text.streakHint}</p>
        )}
      </div>
      {!playful && (
        <div className="grid content-start gap-2">
          <p className="flex justify-between gap-2 font-semibold">
            <span>{text.level(rewards.level)}</span>
            <span className="text-sm font-normal text-muted-foreground tabular-nums">
              {text.xp(rewards.level_xp, rewards.level_size)}
            </span>
          </p>
          <Meter share={rewards.level_xp / rewards.level_size} label={text.level(rewards.level)} />
        </div>
      )}
      <div className="grid content-start gap-2">
        <p className="font-semibold">{goalLine}</p>
        <Meter share={answered / goal} label={goalLine} />
      </div>
    </div>
  );
}

/** Badges (stickers for the youngest): the earned ones with their day, the others with how to earn them. */
export function BadgeList({ badges, copy }: { badges: Rewards["badges"]; copy: Copy }) {
  const text = copy.rewards;
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {badges.map((badge) => (
        <li
          key={badge.code}
          data-earned={Boolean(badge.earned_at)}
          className={cn(
            "grid content-start justify-items-center gap-1 rounded-xl border bg-card p-4 text-center",
            !badge.earned_at && "border-dashed bg-transparent opacity-60 grayscale",
          )}
        >
          <span aria-hidden className="text-3xl playful:text-5xl">
            {BADGE_EMOJI[badge.code] ?? "🏅"}
          </span>
          <span className="font-semibold">{badgeName(copy, badge.code)}</span>
          <span className="text-xs text-muted-foreground">
            {badge.earned_at
              ? text.earnedOn(formatDay(copy.language.locale, badge.earned_at))
              : text.badges[badge.code]?.how}
          </span>
        </li>
      ))}
    </ul>
  );
}
