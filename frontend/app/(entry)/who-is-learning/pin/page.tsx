import { redirect } from "next/navigation";

import { PinForm } from "@/components/pin-form";
import { setPin } from "@/lib/actions/auth";
import { getMe } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.parentPin.handOverTitle);

/**
 * The first hand-over: child mode needs a parent PIN, its only way out. Once it is set, child mode
 * starts as the parent asked (`?child=`, and `practice=` or `test=` to go straight into one).
 */
export default async function HandOverPinPage({ searchParams }: PageProps<"/who-is-learning/pin">) {
  const copy = await getCopy();
  const text = copy.parentPin;
  const [{ pin_set }, query] = await Promise.all([getMe(), searchParams]);
  const [child, practice, test] = ["child", "practice", "test"].map((name) => {
    const value = query[name];
    return typeof value === "string" && value ? value : undefined;
  });
  if (pin_set || !child) redirect("/who-is-learning");

  return (
    <div className="mx-auto grid max-w-xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">🔒 {text.handOverTitle}</h1>
        <p className="text-muted-foreground">{text.handOverText}</p>
      </div>
      <PinForm action={setPin.bind(null, { child, practice, test })} submitLabel={text.saveAndStart} />
    </div>
  );
}
