import { BookUploader } from "@/components/book-uploader";
import { getChosenChild, getOptions } from "@/lib/api";
import { getCopy, titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.upload.title);

export default async function UploadPage() {
  const copy = await getCopy();
  const [{ children, child }, options] = await Promise.all([getChosenChild(), getOptions()]);
  return (
    <div className="grid max-w-3xl gap-6">
      <div className="grid gap-1">
        <h1 className="text-3xl font-extrabold">{copy.upload.title}</h1>
        <p className="text-muted-foreground">{copy.upload.subtitle}</p>
      </div>
      <BookUploader
        newBook={{ options, learners: children, chosenId: child?.id ?? null }}
        limits={options.upload}
      />
    </div>
  );
}
