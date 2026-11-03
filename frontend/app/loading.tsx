import { copy } from "@/lib/copy";

/** Shown while a signed-in page asks the backend for its data. */
export default function Loading() {
  return (
    <div role="status" className="grid min-h-[50dvh] place-items-center text-muted-foreground">
      <span className="flex items-center gap-3">
        <span className="size-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        {copy.loading}
      </span>
    </div>
  );
}
