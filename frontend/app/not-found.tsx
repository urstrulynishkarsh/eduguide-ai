import Link from "next/link";

import { Button } from "@/components/ui/button";
import { getCopy } from "@/lib/copy/server";

export default async function NotFound() {
  const copy = await getCopy();
  return (
    <main className="grid min-h-dvh place-items-center px-4 text-center">
      <div className="grid gap-4">
        <p aria-hidden className="text-5xl">
          🔍
        </p>
        <h1 className="text-2xl font-bold">{copy.notFound.title}</h1>
        <Button asChild className="justify-self-center">
          <Link href="/">{copy.notFound.back}</Link>
        </Button>
      </div>
    </main>
  );
}
