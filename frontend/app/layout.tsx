import type { Metadata, Viewport } from "next";
import { Inter, Nunito } from "next/font/google";

import { copy } from "@/lib/copy";

import "./globals.css";

const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const rounded = Nunito({ subsets: ["latin"], variable: "--font-rounded" });

export const metadata: Metadata = {
  title: { default: copy.appName, template: `%s · ${copy.appName}` },
  description: copy.landing.subtitle,
};

export const viewport: Viewport = { themeColor: "#fbfaf6" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${body.variable} ${rounded.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
