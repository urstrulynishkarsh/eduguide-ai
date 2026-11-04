import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getCopy } from "@/lib/copy/server";

export async function SignOutButton() {
  const copy = await getCopy();
  return (
    <form action="/signout" method="post">
      <Button type="submit" variant="ghost" size="sm" className="text-muted-foreground">
        <LogOut aria-hidden />
        {copy.signOut}
      </Button>
    </form>
  );
}
