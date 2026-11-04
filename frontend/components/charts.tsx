import type { Copy } from "@/lib/copy";
import { cn } from "@/lib/utils";

/*
 * The charts of the dashboard and Progress, drawn on the server (no chart library, no JavaScript in
 * the browser). One y-axis each; thin marks (columns at most 24px with 4px rounded tops and a 2px
 * gap, a 2px line, dots with a ring in the card's colour); a hover / focus readout above the plot;
 * every value also in a table view (`DataTable`) and in each mark's accessible name.
 */

/** The top of the scale: the biggest value, rounded up to a clean number (7 → 7, 23 → 30). */
function scaleTop(biggest: number): number {
  const most = Math.max(biggest, 1);
  const step = 10 ** Math.floor(Math.log10(most));
  return Math.ceil(most / step) * step;
}

/** The readout of the hovered or focused mark, above the plot so it never runs off the card. */
const readout =
  "pointer-events-none absolute inset-x-0 -top-7 hidden text-center text-xs font-medium group-hover:block group-focus:block";
const mark =
  "group flex h-full flex-1 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export interface Column {
  key: string;
  /** Under the column; empty to leave room on a crowded axis. */
  tick: string;
  /** In the readout and the column's accessible name ("Thursday, 29 October"). */
  label: string;
  answered: number;
  correct: number;
}

/**
 * Questions answered per day or week as columns, the part right the first time in full colour (two
 * steps of the layout's primary, checked with the dataviz validator: one hue, lighter, visible).
 */
export function ColumnChart({ columns, label, copy }: { columns: Column[]; label: string; copy: Copy }) {
  const text = copy.dashboard;
  const top = scaleTop(Math.max(...columns.map((column) => column.answered)));
  return (
    <figure className="grid gap-3">
      <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        {[
          ["bg-primary", text.right],
          ["bg-primary-light", text.notRight],
        ].map(([colour, name]) => (
          <li key={name} className="flex items-center gap-1.5">
            <span aria-hidden className={cn("size-2.5 rounded-[2px]", colour)} />
            {name}
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-[auto_1fr] gap-x-2 pt-7">
        <div aria-hidden className="flex flex-col justify-between text-xs text-muted-foreground tabular-nums">
          <span className="-mt-2">{top}</span>
          <span className="-mb-2">0</span>
        </div>
        <div role="group" aria-label={label} className="relative flex h-32 items-end border-y">
          {columns.map((column) => {
            const line = text.dayLine(column.label, column.answered, column.correct);
            return (
              <div
                key={column.key}
                role="img"
                tabIndex={0}
                aria-label={line}
                className={cn(mark, "items-end justify-center")}
              >
                {column.answered > 0 && (
                  <span
                    className="flex w-full max-w-6 flex-col gap-[2px] overflow-hidden rounded-t-[4px] group-hover:opacity-80 group-focus:opacity-80"
                    style={{ height: `${(column.answered / top) * 100}%` }}
                  >
                    {column.answered > column.correct && (
                      <span
                        className="bg-primary-light"
                        style={{ flexGrow: column.answered - column.correct }}
                      />
                    )}
                    {column.correct > 0 && (
                      <span className="bg-primary" style={{ flexGrow: column.correct }} />
                    )}
                  </span>
                )}
                <span aria-hidden className={readout}>
                  {line}
                </span>
              </div>
            );
          })}
        </div>
        <span />
        <div aria-hidden className="flex pt-1 text-xs text-muted-foreground">
          {columns.map((column) => (
            <span key={column.key} className="flex-1 text-center whitespace-nowrap">
              {column.tick}
            </span>
          ))}
        </div>
      </div>
    </figure>
  );
}

export interface Point {
  key: string;
  /** Under the plot at the two ends. */
  tick: string;
  /** In the readout and the point's accessible name. */
  label: string;
  /** A percentage; below 0 when wrong answers lose marks. */
  value: number;
}

/** Percentages over time as a line, the last one labelled. Each point's whole column is its hit area. */
export function LineChart({ points, label }: { points: Point[]; label: string }) {
  const low = Math.min(0, ...points.map((point) => point.value));
  const high = Math.max(100, ...points.map((point) => point.value));
  const x = (i: number) => ((i + 0.5) / points.length) * 100;
  const y = (value: number) => ((value - low) / (high - low)) * 100;
  const last = points.at(-1);
  return (
    <figure className="grid grid-cols-[auto_1fr] gap-x-2 pt-7">
      <div aria-hidden className="flex flex-col justify-between text-xs text-muted-foreground tabular-nums">
        <span className="-mt-2">{Math.round(high)}%</span>
        <span className="-mb-2">{Math.round(low)}%</span>
      </div>
      <div role="group" aria-label={label} className="relative flex h-32 border-y">
        <span
          aria-hidden
          className="absolute inset-x-0 border-t"
          style={{ bottom: `${y((high + low) / 2)}%` }}
        />
        <svg
          aria-hidden
          className="pointer-events-none absolute inset-0 size-full overflow-visible"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <polyline
            points={points.map((point, i) => `${x(i)},${100 - y(point.value)}`).join(" ")}
            fill="none"
            stroke="var(--color-primary)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        {points.map((point, i) => (
          <div key={point.key} role="img" tabIndex={0} aria-label={point.label} className={mark}>
            <span
              aria-hidden
              className="absolute size-2.5 -translate-x-1/2 translate-y-1/2 rounded-full bg-primary ring-2 ring-card group-hover:scale-125 group-focus:scale-125"
              style={{ left: `${x(i)}%`, bottom: `${y(point.value)}%` }}
            />
            <span aria-hidden className={readout}>
              {point.label}
            </span>
          </div>
        ))}
        {last && (
          <span
            aria-hidden
            className="absolute translate-x-2 translate-y-1/2 text-xs font-semibold"
            style={{ left: `${x(points.length - 1)}%`, bottom: `${y(last.value)}%` }}
          >
            {Math.round(last.value)}%
          </span>
        )}
      </div>
      <span />
      <div aria-hidden className="flex justify-between pt-1 text-xs text-muted-foreground">
        <span>{points[0]?.tick}</span>
        {points.length > 1 && <span>{last?.tick}</span>}
      </div>
    </figure>
  );
}

/** A small line of a few values (a chapter's marks in each year's paper), without axes. */
export function Sparkline({ values, label }: { values: number[]; label: string }) {
  const [width, height, pad] = [72, 24, 4];
  const top = Math.max(...values, 1);
  const at = (value: number, i: number) => [
    pad + (i / Math.max(values.length - 1, 1)) * (width - 2 * pad),
    height - pad - (value / top) * (height - 2 * pad),
  ];
  const [endX, endY] = at(values.at(-1) ?? 0, values.length - 1);
  return (
    <svg role="img" aria-label={label} width={width} height={height} className="shrink-0 overflow-visible">
      <title>{label}</title>
      <polyline
        points={values.map((value, i) => at(value, i).join(",")).join(" ")}
        fill="none"
        stroke="var(--color-primary-light)"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={endX}
        cy={endY}
        r={4}
        fill="var(--color-primary)"
        stroke="var(--color-card)"
        strokeWidth={2}
      />
    </svg>
  );
}

/** A chart's numbers as a table, folded away until asked for. */
export function DataTable({ summary, head, rows }: { summary: string; head: string[]; rows: string[][] }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer font-semibold text-primary">{summary}</summary>
      <table className="mt-2 w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            {head.map((name) => (
              <th key={name} scope="col" className="py-1 pr-3 font-medium">
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {rows.map(([first, ...rest], row) => (
            <tr key={row} className="border-t">
              <th scope="row" className="py-1 pr-3 font-medium">
                {first}
              </th>
              {rest.map((cell, i) => (
                <td key={i} className="py-1 pr-3">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
