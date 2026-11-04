import { Lock } from "lucide-react";
import Link from "next/link";

import { LanguagePicker } from "@/components/language-picker";
import { Logo } from "@/components/logo";
import { NavLinks } from "@/components/nav-links";
import { SignOutButton } from "@/components/sign-out-button";
import { Button } from "@/components/ui/button";
import { getLearner } from "@/lib/api";
import { getCopy } from "@/lib/copy/server";

/**
 * The student area. The learner's class profile picks one of four layouts (`ui_mode`) and which
 * menu items exist (`features`); the pages are the same for every class (docs/04 §4.4).
 */
export default async function LearnLayout({ children }: LayoutProps<"/learn">) {
  const copy = await getCopy();
  const { me, classProfile } = await getLearner();
  const childMode = me.user.role === "parent";

  return (
    <div data-ui-mode={classProfile.ui_mode} className="min-h-dvh bg-background pb-28 sm:pb-0">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3 sm:px-6">
        <Logo href="/learn" />
        <nav
          aria-label={copy.learn.nav}
          className="fixed inset-x-0 bottom-0 z-10 border-t bg-card/95 px-2 py-2 backdrop-blur sm:static sm:min-w-0 sm:flex-1 sm:border-0 sm:bg-transparent sm:p-0 sm:standard:order-last sm:standard:basis-full sm:dense:order-last sm:dense:basis-full"
        >
          <NavLinks area={classProfile.ui_mode} features={classProfile.features} />
        </nav>
        {childMode ? (
          <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
            <Link href="/learn/exit">
              <Lock aria-hidden />
              {copy.learn.switchLearner}
            </Link>
          </Button>
        ) : (
          <div className="flex items-center gap-1">
            <LanguagePicker />
            <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
              <Link href="/onboarding/profile">{copy.learn.myClassDetails}</Link>
            </Button>
            <SignOutButton />
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
