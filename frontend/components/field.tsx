import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * `autoComplete` for a field the browser must not fill from the signed-in person's saved details,
 * such as one whose label says "name" but means a book's, a child's or a board's. Chrome ignores
 * "off" there and offers the person's own name; on computers it leaves alone a value it doesn't
 * recognise, and "none" is one that accessibility checkers (axe) accept.
 */
export const NO_AUTOFILL = "none";

interface FieldProps extends React.ComponentProps<typeof Input> {
  name: string;
  label: string;
  hint?: string;
  error?: string;
}

/** A labelled text input with its hint and the backend's message for it. */
export function Field({ name, label, hint, error, ...inputProps }: FieldProps) {
  const describedBy = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div className="grid content-start gap-2">
      <Label htmlFor={name}>{label}</Label>
      <Input
        id={name}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        {...inputProps}
      />
      {error ? (
        <p id={`${name}-error`} className="text-sm text-destructive">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${name}-hint`} className="text-sm text-muted-foreground">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
