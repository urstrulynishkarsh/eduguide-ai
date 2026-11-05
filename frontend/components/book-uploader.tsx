"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useCopy } from "@/components/copy-provider";
import { Field, NO_AUTOFILL } from "@/components/field";
import { FormMessage } from "@/components/form-message";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { createBook } from "@/lib/actions/books";
import { said } from "@/lib/copy";
import type { FormState, Refusal } from "@/lib/forms";
import type { OnboardingOptions, Student } from "@/lib/types";

const selectClass =
  "h-9 rounded-md border border-input bg-card px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

/** Sends the file to the upload route, reporting how much has gone (fetch cannot report that). */
function send(bookId: string, file: File, onProgress: (percent: number) => void) {
  return new Promise<{ status: number; error?: Refusal }>((resolve) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/api/books/${encodeURIComponent(bookId)}/documents`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onload = () => {
      let error: Refusal | undefined;
      try {
        error = JSON.parse(request.responseText)?.error;
      } catch {
        // Not JSON: the generic message is shown.
      }
      resolve({ status: request.status, error });
    };
    request.onerror = () => resolve({ status: 0, error: { code: "unreachable" } });
    const body = new FormData();
    body.append("file", file);
    request.send(body);
  });
}

interface NewBook {
  options: OnboardingOptions;
  learners: Student[];
  chosenId: string | null;
}

/**
 * "Upload Book". Without `bookId` it first creates the book from the fields, then sends the file
 * and opens the book, where the reading checklist follows. With `bookId` it adds a file to it.
 */
export function BookUploader({
  bookId,
  newBook,
  limits,
}: {
  bookId?: string;
  newBook?: NewBook;
  limits: OnboardingOptions["upload"];
}) {
  const copy = useCopy();
  const text = copy.upload;
  const router = useRouter();
  const [state, setState] = useState<FormState>({});
  const [percent, setPercent] = useState<number | null>(null);
  const [forWhom, setForWhom] = useState(newBook?.chosenId ?? "");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = (form.elements.namedItem("file") as HTMLInputElement).files?.[0];
    if (!file?.size) return;
    if (file.size > limits.max_file_mb * 1024 * 1024) {
      setState({ fieldErrors: { file: text.tooBig(limits.max_file_mb) } });
      return;
    }
    setPercent(0);
    let target = bookId;
    if (!target) {
      // The fields only: the file goes to the upload route below, as a Server Action takes at most 1 MB.
      const fields = new FormData(form);
      fields.delete("file");
      const created = await createBook({}, fields);
      if (!created.bookId) {
        setState(created);
        setPercent(null);
        return;
      }
      target = created.bookId;
    }
    const result = await send(target, file, setPercent);
    if (result.status === 202) {
      setState({});
      setPercent(null);
      if (bookId) router.refresh();
      else router.push(`/parent/books/${target}`);
    } else {
      // A book made a moment ago stays: the file can be sent again from its page.
      setState(result.error ?? { message: text.failed });
      setPercent(null);
      if (!bookId) router.push(`/parent/books/${target}`);
    }
  }

  const errors = state.fieldErrors ?? {};
  const sending = percent !== null;
  return (
    <form onSubmit={submit} className="grid gap-4">
      {newBook && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              name="title"
              label={text.bookTitle}
              placeholder={text.bookTitlePlaceholder}
              required
              maxLength={200}
              autoComplete={NO_AUTOFILL}
              error={errors.title}
            />
            <Field
              name="subject"
              label={text.subject}
              placeholder={text.subjectPlaceholder}
              required
              maxLength={60}
              error={errors.subject}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid content-start gap-2">
              <Label htmlFor="material_type">{text.materialType}</Label>
              <select id="material_type" name="material_type" className={selectClass}>
                {newBook.options.material_types.map((option) => (
                  <option key={option.code} value={option.code}>
                    {said(copy.options.material_types, option.code, option.label)}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid content-start gap-2">
              <Label htmlFor="student_id">{text.forWhom}</Label>
              <select
                id="student_id"
                name="student_id"
                value={forWhom}
                onChange={(event) => setForWhom(event.target.value)}
                className={selectClass}
              >
                {newBook.learners.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.name}
                  </option>
                ))}
                <option value="">{text.family}</option>
              </select>
            </div>
          </div>
          {!forWhom && (
            <div className="grid content-start gap-2 sm:w-1/2">
              <Label htmlFor="class_level">{copy.profileForm.classTitle}</Label>
              <select
                id="class_level"
                name="class_level"
                defaultValue={newBook.learners[0]?.profile?.class_level}
                className={selectClass}
              >
                {newBook.options.classes.map((option) => (
                  <option key={option.class_level} value={option.class_level}>
                    {said(copy.options.classes, option.class_level, option.label)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </>
      )}
      <Field
        name="file"
        label={text.file}
        hint={text.fileHint(limits.accepted_extensions.join(", "), limits.max_file_mb)}
        type="file"
        accept={limits.accepted_extensions.join(",")}
        required
        error={errors.file}
        className="h-auto py-2"
      />
      <FormMessage error={state} />
      {sending && (
        <div className="grid gap-1" role="status">
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: `${percent}%` }} />
          </div>
          <p className="text-sm text-muted-foreground">{text.sending(percent)}</p>
        </div>
      )}
      <Button type="submit" disabled={sending} className="justify-self-start">
        {text.submit}
      </Button>
    </form>
  );
}
