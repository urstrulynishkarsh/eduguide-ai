import type { Metadata, Viewport } from "next";
import { Inter, Noto_Sans_Devanagari, Nunito } from "next/font/google";
import { Suspense } from "react";

import Loading from "@/app/loading";
import { CopyProvider } from "@/components/copy-provider";
import { APP_NAME, copyFor } from "@/lib/copy";
import { currentLanguage, getCopy } from "@/lib/copy/server";

import "./globals.css";

const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const rounded = Nunito({ subsets: ["latin"], variable: "--font-rounded" });
// Hindi letters, which the other two don't have; fetched only by pages that show some.
const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  variable: "--font-devanagari",
  preload: false,
});

export async function generateMetadata(): Promise<Metadata> {
  const copy = await getCopy();
  return { title: { default: APP_NAME, template: `%s · ${APP_NAME}` }, description: copy.landing.subtitle };
}

export const viewport: Viewport = { themeColor: "#fbfaf6" };

/** Every screen in the device's screen language: client components read it through `useCopy()`. */
async function InLanguage({ children }: { children: React.ReactNode }) {
  const language = await currentLanguage();
  return (
    <CopyProvider language={language}>
      {/* The page is in the screen language; <html> can't wait for the cookie under Cache Components. */}
      <div lang={copyFor(language).language.htmlLang} className="contents">
        {children}
      </div>
    </CopyProvider>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${body.variable} ${rounded.variable} ${devanagari.variable}`}>
      <body className="min-h-dvh">
        <Suspense fallback={<Loading />}>
          <InLanguage>{children}</InLanguage>
        </Suspense>
      </body>
    </html>
  );
}
