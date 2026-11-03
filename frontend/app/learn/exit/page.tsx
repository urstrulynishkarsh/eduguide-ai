import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getMe } from "@/lib/api";
import { copy } from "@/lib/copy";

import { ExitForm } from "./exit-form";

const text = copy.exitChildMode;

export const metadata: Metadata = { title: text.title };

/** Leaving child mode needs the parent's password (docs/04 §4.6). */
export default async function ExitChildModePage() {
  const me = await getMe();
  if (me.user.role !== "parent") redirect("/learn"); // a student who signed up alone has nothing to leave

  return (
    <div className="mx-auto grid max-w-sm gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">🔒 {text.title}</h1>
        <p className="text-muted-foreground">{text.text}</p>
      </div>
      <ExitForm />
      <Button asChild variant="ghost" className="justify-self-start">
        <Link href="/learn">← {text.back}</Link>
      </Button>
    </div>
  );
}
