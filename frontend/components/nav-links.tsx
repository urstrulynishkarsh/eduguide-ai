"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { copy } from "@/lib/copy";
import { PARENT_NAV, studentNav, type NavItem } from "@/lib/navigation";
import type { ClassFeatures, UIMode } from "@/lib/types";
import { cn } from "@/lib/utils";

type NavLinksProps = { area: "parent" } | { area: UIMode; features: ClassFeatures };

const itemClass = cn(
  "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors",
  "playful:flex-col playful:gap-1 playful:rounded-2xl playful:px-5 playful:py-2 playful:text-lg playful:font-bold",
  "friendly:flex-col friendly:gap-0.5 friendly:px-4 friendly:text-base friendly:font-semibold sm:friendly:flex-row sm:friendly:gap-2",
  // Class 6 - 12 on a phone: a tab bar, icon above a short label.
  "max-sm:standard:flex-col max-sm:standard:gap-0.5 max-sm:standard:px-1 max-sm:standard:text-[0.6875rem]",
  "max-sm:dense:flex-col max-sm:dense:gap-0.5 max-sm:dense:px-1 max-sm:dense:text-[0.6875rem]",
  "sm:dense:px-2.5 sm:dense:py-1.5",
);

function isActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/learn" && pathname.startsWith(`${href}/`));
}

/** The menu of the parent area or of the learner's layout. Items of later steps say "Soon". */
export function NavLinks(props: NavLinksProps) {
  const pathname = usePathname();
  const items: NavItem[] = props.area === "parent" ? PARENT_NAV : studentNav(props.area, props.features);
  const showEmoji = props.area === "playful" || props.area === "friendly";

  return (
    <ul
      className={cn(
        "flex gap-1 overflow-x-auto",
        props.area === "parent"
          ? "lg:flex-col lg:overflow-visible"
          : "justify-around max-sm:gap-0 sm:justify-start",
      )}
    >
      {items.map((item) => {
        const content = (
          <>
            {showEmoji && item.emoji ? (
              <span aria-hidden className="text-xl playful:text-3xl">
                {item.emoji}
              </span>
            ) : (
              <item.icon aria-hidden className="size-4" />
            )}
            <span>{copy.nav[item.label]}</span>
            {item.soon && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[0.625rem] leading-none font-semibold tracking-wide text-muted-foreground uppercase max-sm:standard:hidden max-sm:dense:hidden">
                {copy.soon}
              </span>
            )}
          </>
        );
        return (
          <li key={item.label}>
            {item.soon ? (
              <span aria-disabled className={cn(itemClass, "cursor-default text-muted-foreground")}>
                {content}
              </span>
            ) : (
              <Link
                href={item.href}
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
                className={cn(
                  itemClass,
                  "hover:bg-secondary aria-[current=page]:bg-secondary aria-[current=page]:text-secondary-foreground",
                )}
              >
                {content}
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}
