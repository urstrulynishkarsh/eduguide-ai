import { CheckCircle2, Circle, LoaderCircle, XCircle } from "lucide-react";

import { copy } from "@/lib/copy";
import type { BookDocument } from "@/lib/types";

type State = BookDocument["progress"][number]["state"];

/**
 * The reading progress of one file, in parent words (docs/04 §4.5). Backend steps that share a
 * label ("Getting practice ready") are shown as one line.
 */
export function stepsInParentWords(progress: BookDocument["progress"]): { label: string; state: State }[] {
  const lines: { label: string; states: State[] }[] = [];
  for (const { step, state } of progress) {
    const label = copy.upload.steps[step] ?? step;
    const last = lines.at(-1);
    if (last?.label === label) last.states.push(state);
    else lines.push({ label, states: [state] });
  }
  return lines.map(({ label, states }) => ({
    label,
    state:
      (["failed", "active"] as const).find((s) => states.includes(s)) ??
      (states.every((s) => s === "done") ? "done" : "pending"),
  }));
}

const ICONS = {
  done: <CheckCircle2 aria-hidden className="size-4 text-success" />,
  active: <LoaderCircle aria-hidden className="size-4 animate-spin text-primary" />,
  failed: <XCircle aria-hidden className="size-4 text-destructive" />,
  pending: <Circle aria-hidden className="size-4 text-muted-foreground/50" />,
};

export function DocumentChecklist({ document }: { document: BookDocument }) {
  return (
    <ul className="grid gap-1.5 text-sm">
      {stepsInParentWords(document.progress).map((line) => (
        <li key={line.label} className="flex items-center gap-2" data-state={line.state}>
          {ICONS[line.state]}
          <span className={line.state === "pending" ? "text-muted-foreground" : undefined}>{line.label}</span>
        </li>
      ))}
    </ul>
  );
}
