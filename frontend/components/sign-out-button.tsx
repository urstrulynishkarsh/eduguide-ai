import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { copy } from "@/lib/copy";

export function SignOutButton() {
  return (
    <form action="/signout" method="post">
      <Button type="submit" variant="ghost" size="sm" className="text-muted-foreground">
        <LogOut aria-hidden />
        {copy.signOut}
      </Button>
    </form>
  );
}
