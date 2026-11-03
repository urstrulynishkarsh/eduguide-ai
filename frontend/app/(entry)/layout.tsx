import { Logo } from "@/components/logo";

/** Sign-in, sign-up and onboarding: one calm column, nothing else on screen. */
export default function EntryLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col px-4 sm:px-6">
      <header className="py-5">
        <Logo />
      </header>
      <main className="flex-1 pt-4 pb-16">{children}</main>
    </div>
  );
}
