import type { Metadata } from "next";
import Link from "next/link";

import { copy } from "@/lib/copy";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: copy.login.submit };

export default function LoginPage() {
  return (
    <div className="mx-auto grid max-w-sm gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.login.title}</h1>
        <p className="text-muted-foreground">{copy.login.subtitle}</p>
      </div>
      <LoginForm />
      <p className="text-sm text-muted-foreground">
        {copy.login.noAccount}{" "}
        <Link href="/register" className="font-semibold text-primary underline-offset-4 hover:underline">
          {copy.login.createAccount}
        </Link>
      </p>
    </div>
  );
}
