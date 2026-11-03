import type { Metadata } from "next";
import Link from "next/link";

import { copy } from "@/lib/copy";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: copy.register.submit };

export default function RegisterPage() {
  return (
    <div className="mx-auto grid max-w-md gap-6">
      <h1 className="text-3xl font-extrabold">{copy.register.title}</h1>
      <RegisterForm />
      <p className="text-sm text-muted-foreground">
        {copy.register.haveAccount}{" "}
        <Link href="/login" className="font-semibold text-primary underline-offset-4 hover:underline">
          {copy.register.signIn}
        </Link>
      </p>
    </div>
  );
}
