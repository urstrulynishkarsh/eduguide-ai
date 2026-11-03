import { cn } from "@/lib/utils";

const COLOURS = [
  "bg-orange-100 text-orange-700",
  "bg-sky-100 text-sky-700",
  "bg-emerald-100 text-emerald-700",
  "bg-violet-100 text-violet-700",
  "bg-rose-100 text-rose-700",
  "bg-amber-100 text-amber-800",
];

/** A round initial in a colour that stays the same for the same name. */
export function ChildAvatar({ name, className }: { name: string; className?: string }) {
  const colour = COLOURS[[...name].reduce((sum, char) => sum + char.codePointAt(0)!, 0) % COLOURS.length];
  return (
    <span
      aria-hidden
      className={cn(
        "grid size-12 shrink-0 place-items-center rounded-full font-display text-xl font-bold",
        colour,
        className,
      )}
    >
      {[...name][0]?.toUpperCase()}
    </span>
  );
}
