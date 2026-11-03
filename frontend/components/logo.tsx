import Link from "next/link";

import { copy } from "@/lib/copy";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link
      href={href}
      className="inline-flex shrink-0 items-center gap-2 font-display whitespace-nowrap text-lg font-extrabold tracking-tight"
    >
      <span
        aria-hidden
        className="grid size-8 place-items-center rounded-lg bg-primary text-base text-primary-foreground"
      >
        📖
      </span>
      {copy.appName}
    </Link>
  );
}
