"use client";

import { Delete } from "lucide-react";
import { useActionState, useId, useState } from "react";
import { flushSync } from "react-dom";

import { useCopy } from "@/components/copy-provider";
import { Button } from "@/components/ui/button";
import type { PinState } from "@/lib/actions/auth";

/** As the backend's `PIN_LENGTH`. */
const PIN_LENGTH = 4;
const DIGITS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

interface PinPadProps {
  /** The form field the PIN is sent as. */
  name: string;
  label: string;
  error?: string;
  /** Called once the last digit is in (and in the form), to send the form straight away. */
  onComplete?: () => void;
}

/**
 * A PIN form's action state, with how many answers it has had: the `key` of the form's pads, so they
 * start again empty after each answer (a wrong PIN, a saved one), and not a moment later.
 */
export function usePinFormState(action: (state: PinState, formData: FormData) => Promise<PinState>) {
  return useActionState(
    async (previous: PinState & { answers: number }, formData: FormData) => ({
      ...(await action(previous, formData)),
      answers: previous.answers + 1,
    }),
    { answers: 0 },
  );
}

/**
 * The parent PIN, typed on on-screen buttons: there is no text field, so a password manager has
 * nothing to fill in and a phone keyboard nothing to learn. The digits go with the form in a hidden
 * field; the form starts the pad again with a new `key` (`usePinFormState`). The number keys and
 * Backspace work too while a button of the pad has focus (the buttons are never disabled, so focus
 * stays). A screen reader hears how many digits are in, never which.
 */
export function PinPad({ name, label, error, onComplete }: PinPadProps) {
  const copy = useCopy();
  const id = useId();
  const [pin, setPin] = useState("");

  const type = (digit: string) => {
    if (pin.length === PIN_LENGTH) return;
    const typed = pin + digit;
    flushSync(() => setPin(typed)); // in the hidden field before the form is sent
    if (typed.length === PIN_LENGTH) onComplete?.();
  };
  const erase = () => setPin(pin.slice(0, -1));
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (/^[0-9]$/.test(event.key)) type(event.key);
    else if (event.key === "Backspace") erase();
    else return;
    event.preventDefault();
  };

  return (
    <div
      role="group"
      aria-labelledby={`${id}-label`}
      aria-describedby={error ? `${id}-error` : undefined}
      onKeyDown={onKeyDown}
      className="grid w-full max-w-64 gap-3"
    >
      <span id={`${id}-label`} className="text-sm leading-none font-medium">
        {label}
      </span>
      <input type="hidden" name={name} value={pin} />
      <div aria-hidden className="flex justify-center gap-3 py-1">
        {Array.from({ length: PIN_LENGTH }, (_, place) => (
          <span
            key={place}
            className={`size-4 rounded-full border-2 border-primary ${place < pin.length ? "bg-primary" : ""}`}
          />
        ))}
      </div>
      <p className="sr-only" aria-live="polite">
        {copy.pinPad.entered(pin.length)}
      </p>
      <div className="grid grid-cols-3 gap-2">
        {DIGITS.map((digit) => (
          <PadButton key={digit} onClick={() => type(digit)}>
            {digit}
          </PadButton>
        ))}
        <PadButton className="col-start-2" onClick={() => type("0")}>
          0
        </PadButton>
        <PadButton onClick={erase} aria-label={copy.pinPad.erase}>
          <Delete aria-hidden className="size-6" />
        </PadButton>
      </div>
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function PadButton({ className = "", ...props }: React.ComponentProps<typeof Button>) {
  return (
    <Button
      type="button"
      variant="outline"
      className={`h-14 font-display text-2xl ${className}`}
      {...props}
    />
  );
}
