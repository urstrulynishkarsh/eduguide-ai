"use client";

import { useCopy } from "@/components/copy-provider";

/**
 * Shown while a signed-in page asks the backend for its data.
 *
 * Every page that loads data re-exports this as its own loading.tsx. Moving between pages re-renders
 * only what is below the layout they share, and a loading boundary shows only when its own folder is
 * entered, so each page needs one. Without it a tap waits on the server with no sign of life, and the
 * dev server reports "uncached data during prerendering or a navigation".
 */
export default function Loading() {
  const copy = useCopy();
  return (
    <div role="status" className="grid min-h-[50dvh] place-items-center text-muted-foreground">
      <span className="flex items-center gap-3">
        <span className="size-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        {copy.loading}
      </span>
    </div>
  );
}
