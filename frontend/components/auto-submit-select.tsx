"use client";

/** A <select> that sends its form as soon as something is chosen (the source picker reloads the page). */
export function AutoSubmitSelect(props: React.ComponentProps<"select">) {
  return <select {...props} onChange={(event) => event.currentTarget.form?.requestSubmit()} />;
}
