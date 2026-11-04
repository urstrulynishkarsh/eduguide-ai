import Link from "next/link";

import { getCopy, titled } from "@/lib/copy/server";

import { LoginForm } from "./login-form";

export const generateMetadata = titled((copy) => copy.login.submit);

export default async function LoginPage() {
  const copy = await getCopy();
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
