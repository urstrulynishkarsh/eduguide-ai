import { LanguagePicker } from "@/components/language-picker";
import { SignOutButton } from "@/components/sign-out-button";
import { getMe } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.parent.settingsTitle);

export default async function SettingsPage() {
  const copy = await getCopy();
  const text = copy.parent;
  const { user } = await getMe();
  const rows: [string, React.ReactNode][] = [
    [text.name, user.full_name],
    [text.email, user.email],
    // The account's language: every screen, on every device it signs in on.
    [text.language, <LanguagePicker key="language" />],
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
