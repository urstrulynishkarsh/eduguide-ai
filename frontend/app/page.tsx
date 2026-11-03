import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { copy } from "@/lib/copy";

const text = copy.landing;

export default function LandingPage() {
  return (
    <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between py-5">
        <Logo />
        <nav className="flex items-center gap-2">
          <Button asChild variant="ghost">
            <Link href="/login">{text.signIn}</Link>
          </Button>
          <Button asChild className="hidden sm:inline-flex">
            <Link href="/register">{text.getStarted}</Link>
          </Button>
        </nav>
      </header>

      <main className="flex-1">
        <section className="grid items-center gap-12 py-12 lg:grid-cols-[1.1fr_0.9fr] lg:py-20">
          <div className="grid gap-6">
            <h1 className="text-4xl leading-tight font-extrabold tracking-tight text-balance sm:text-5xl">
              {text.title}
            </h1>
            <p className="max-w-xl text-lg text-pretty text-muted-foreground">{text.subtitle}</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="h-12 px-7 text-base">
                <Link href="/register">
                  {text.getStarted} <ArrowRight aria-hidden />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="h-12 px-7 text-base">
                <a href="#how-it-works">{text.seeHow}</a>
              </Button>
            </div>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldCheck aria-hidden className="size-4 text-success" />
              {text.trust}
            </p>
          </div>
          <PracticePreview />
        </section>

        <section id="how-it-works" className="scroll-mt-8 py-12">
          <h2 className="mb-8 text-center text-3xl font-bold">{text.howTitle}</h2>
          <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {text.steps.map((step, index) => (
              <li key={step.title} className="relative grid gap-2 rounded-2xl border bg-card p-6 shadow-sm">
                <span aria-hidden className="text-3xl">
                  {step.emoji}
                </span>
                <h3 className="text-xl font-bold">
                  <span className="mr-2 text-primary">{index + 1}.</span>
                  {step.title}
                </h3>
                <p className="text-muted-foreground">{step.text}</p>
              </li>
            ))}
          </ol>
          <p aria-hidden className="mt-6 text-center font-display text-lg font-bold text-primary">
            {text.steps.map((step) => step.title).join(" → ")}
          </p>
        </section>

        <section className="py-12">
          <h2 className="text-center text-3xl font-bold">{text.classesTitle}</h2>
          <p className="mt-2 mb-8 text-center text-muted-foreground">{text.classesText}</p>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {text.groups.map((group, index) => (
              <li
                key={group.title}
                // Each card wears the colours of the layout that group of classes really gets.
                data-ui-mode={(["playful", "friendly", "standard", "dense"] as const)[index]}
                className="grid content-start gap-2 rounded-lg border bg-background p-6"
              >
                <span aria-hidden className="text-3xl">
                  {group.emoji}
                </span>
                <h3 className="text-lg font-bold text-primary">{group.title}</h3>
                <p className="text-sm text-muted-foreground">{group.text}</p>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="border-t py-6 text-center text-sm text-muted-foreground">© {copy.appName}</footer>
    </div>
  );
}

/** A Nursery-style question, the kind spec §5 asks for, as a picture of what children see. */
function PracticePreview() {
  return (
    <div
      aria-hidden
      data-ui-mode="playful"
      className="mx-auto grid w-full max-w-sm gap-5 rounded-3xl border-4 border-accent bg-background p-7 shadow-xl"
    >
      <p className="text-center text-2xl font-extrabold">{text.preview.question}</p>
      <div className="grid grid-cols-3 gap-3">
        {text.preview.choices.map((choice) => (
          <div
            key={choice.label}
            className={
              choice.correct
                ? "grid place-items-center gap-1 rounded-2xl border-4 border-success bg-card p-3"
                : "grid place-items-center gap-1 rounded-2xl border-2 bg-card p-3"
            }
          >
            <span className="text-5xl">{choice.emoji}</span>
            <span className="font-bold">{choice.label}</span>
          </div>
        ))}
      </div>
      <p className="text-center text-xl font-extrabold text-success">{text.preview.praise}</p>
    </div>
  );
}
