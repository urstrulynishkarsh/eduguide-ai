import { ChildSwitcher } from "@/components/child-switcher";
import { Logo } from "@/components/logo";
import { NavLinks } from "@/components/nav-links";
import { SignOutButton } from "@/components/sign-out-button";
import { getChosenChild } from "@/lib/api";
import { getCopy } from "@/lib/copy/server";

/** The parent area: a calm menu (a sidebar on wide screens, a scrolling strip on phones). */
export default async function ParentLayout({ children }: LayoutProps<"/parent">) {
  const copy = await getCopy();
  const { children: learners, child } = await getChosenChild();
  return (
    <div className="mx-auto min-h-dvh max-w-6xl lg:grid lg:grid-cols-[15rem_1fr] lg:gap-8 lg:px-6">
      <aside className="sticky top-0 z-10 border-b bg-background/95 px-4 backdrop-blur lg:h-dvh lg:border-r lg:border-b-0 lg:px-0 lg:py-6 lg:pr-4">
        <div className="flex items-center justify-between py-3 lg:mb-6 lg:block lg:py-0">
          <Logo href="/who-is-learning" />
          <div className="lg:hidden">
            <SignOutButton />
          </div>
        </div>
        <nav aria-label={copy.parent.nav} className="-mx-1 pb-2 lg:mx-0">
          <NavLinks area="parent" />
        </nav>
        <div className="mt-6 hidden lg:block">
          <SignOutButton />
        </div>
      </aside>
      <main className="grid content-start gap-6 px-4 py-6 lg:px-0">
        {child && (
          <div className="flex justify-end">
            <ChildSwitcher items={learners} chosenId={child.id} />
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
