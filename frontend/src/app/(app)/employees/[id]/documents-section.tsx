"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { NativeSelect } from "@/components/app/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { DOCUMENT_ACCEPT, DOCUMENT_LABELS, fileHref, MAX_UPLOAD_MB } from "@/lib/employees";
import { formatDate } from "@/lib/format";
import { useDeleteDocument, useDocuments, useUploadDocument } from "@/lib/queries";

export function DocumentsSection({
  employeeId,
  canUpload,
  canDelete,
}: {
  employeeId: number;
  canUpload: boolean;
  canDelete: boolean;
}) {
  const documents = useDocuments(employeeId);
  const remove = useDeleteDocument(employeeId);

  return (
    <div className="grid gap-6">
      {documents.isPending ? (
        <Skeleton className="h-20 w-full" />
      ) : documents.isError ? (
        <p role="alert">Не вдалося завантажити документи: {documents.error.message}</p>
      ) : documents.data.length === 0 ? (
        <p className="text-slate">Документів ще немає.</p>
      ) : (
        <ul className="grid gap-3">
          {documents.data.map((doc) => (
            <li key={doc.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span>
                <a
                  href={fileHref(doc.file)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-primary underline-offset-4 hover:underline"
                >
                  {doc.title || DOCUMENT_LABELS[doc.document_type ?? "other"]}
                </a>
                <span className="block text-sm text-slate">
                  {DOCUMENT_LABELS[doc.document_type ?? "other"]}, завантажено{" "}
                  {formatDate(doc.uploaded_at)}
                  {doc.uploaded_by && ` (${doc.uploaded_by})`}
                </span>
              </span>
              {canDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={remove.isPending}
                  onClick={() =>
                    remove.mutate(doc.id!, {
                      onSuccess: () => toast.success("Документ видалено"),
                      onError: (error) => toast.error(error.message),
                    })
                  }
                >
                  Видалити документ
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canUpload && <UploadForm employeeId={employeeId} />}
    </div>
  );
}

function UploadForm({ employeeId }: { employeeId: number }) {
  const upload = useUploadDocument(employeeId);
  const formRef = useRef<HTMLFormElement>(null);
  const [error, setError] = useState<string | null>(null);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const data = new FormData(event.currentTarget);
    const file = data.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Оберіть файл.");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`Файл завеликий: максимум ${MAX_UPLOAD_MB} МБ.`);
      return;
    }
    upload.mutate(data, {
      onSuccess: () => {
        formRef.current?.reset();
        toast.success("Документ завантажено");
      },
      onError: (err) =>
        setError(err instanceof ApiError ? (err.fieldErrors.file ?? err.message) : err.message),
    });
  }

  return (
    <form ref={formRef} onSubmit={submit} className="grid max-w-xl gap-4 rounded-md bg-mist p-4">
      <p className="text-sm font-medium">Завантажити документ</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor="document_type">Тип</Label>
          <NativeSelect id="document_type" name="document_type" defaultValue="other" className="bg-sheet">
            {Object.entries(DOCUMENT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="title">Назва (необов&apos;язково)</Label>
          <Input id="title" name="title" maxLength={255} className="h-10 bg-sheet" />
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="file">Файл</Label>
        <Input id="file" name="file" type="file" accept={DOCUMENT_ACCEPT} className="h-10 bg-sheet" />
        <p className="text-xs text-slate">PDF, Word, ODT, JPG або PNG, до {MAX_UPLOAD_MB} МБ.</p>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div>
        <Button type="submit" disabled={upload.isPending}>
          {upload.isPending ? "Завантажуємо…" : "Завантажити документ"}
        </Button>
      </div>
    </form>
  );
}
