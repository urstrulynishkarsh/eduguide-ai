import type { Metadata } from "next";

import { SignOutButton } from "@/components/sign-out-button";
import { getMe, getOptions } from "@/lib/api";
import { copy } from "@/lib/copy";

const text = copy.parent;

export const metadata: Metadata = { title: text.settingsTitle };

export default async function SettingsPage() {
  const [{ user }, options] = await Promise.all([getMe(), getOptions()]);
  const language = options.languages.find((option) => option.code === user.preferred_language);
  const rows = [
    [text.name, user.full_name],
    [text.email, user.email],
    [text.language, language?.label ?? user.preferred_language],
  ];

  return (
    <div className="grid max-w-xl gap-6">
      <h1 className="text-3xl font-extrabold">{text.settingsTitle}</h1>
      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-lg font-bold">{text.account}</h2>
        <dl className="grid gap-3">
          {rows.map(([term, value]) => (
            <div key={term} className="grid gap-0.5 sm:grid-cols-[10rem_1fr]">
              <dt className="text-sm text-muted-foreground">{term}</dt>
              <dd className="font-medium break-all">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <SignOutButton />
    </div>
  );
}
