import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * A field's `autoComplete` unless it says what it is (`"email"`, `"current-password"`…). Left to
 * guess, Chrome fills the signed-in person's saved details into fields that aren't theirs (their
 * own name into "Book name", "Child's name"), and it ignores "off" there. On computers it leaves
 * alone a value it doesn't recognise, and "none" is one that accessibility checkers (axe) accept.
 */
const NO_AUTOFILL = "none";

interface FieldProps extends React.ComponentProps<typeof Input> {
  name: string;
  label: string;
  hint?: string;
  error?: string;
}

/**
 * A labelled text input with its hint and the backend's message for it. The browser fills it only
 * when `autoComplete` names what it holds.
 */
export function Field({ name, label, hint, error, autoComplete = NO_AUTOFILL, ...inputProps }: FieldProps) {
  const describedBy = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div className="grid content-start gap-2">
      <Label htmlFor={name}>{label}</Label>
      <Input
        id={name}
        name={name}
        autoComplete={autoComplete}
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
