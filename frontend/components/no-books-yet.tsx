import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { Copy } from "@/lib/copy";

/**
 * A learner screen with no books to work from. A child is told a grown-up uploads them (`words`); a
 * student who signed up alone (`solo`) is sent to their own My Books.
 */
export function NoBooksYet({ copy, solo, words }: { copy: Copy; solo: boolean; words: string }) {
  if (!solo) return <p className="text-muted-foreground playful:text-2xl">{words}</p>;
  return (
    <div className="grid justify-items-start gap-3">
      <p className="text-muted-foreground">{copy.learn.noBooksSolo}</p>
      <Button asChild>
        <Link href="/learn/books">{copy.library.upload}</Link>
      </Button>
    </div>
  );
}
