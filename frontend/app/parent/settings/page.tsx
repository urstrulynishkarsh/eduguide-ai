import { LanguagePicker } from "@/components/language-picker";
import { PinForm } from "@/components/pin-form";
import { SignOutButton } from "@/components/sign-out-button";
import { setPin } from "@/lib/actions/auth";
import { getMe } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.parent.settingsTitle);

export default async function SettingsPage() {
  const copy = await getCopy();
  const text = copy.parent;
  const { user, pin_set } = await getMe();
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
      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <h2 className="mb-1 text-lg font-bold">{copy.parentPin.title}</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          {pin_set ? copy.parentPin.isSet : copy.parentPin.notSet}
        </p>
        <PinForm action={setPin.bind(null, null)} submitLabel={copy.parentPin.save} />
      </section>
      <SignOutButton />
    </div>
  );
}
