"use client";

import { DragEvent, FormEvent, useEffect, useMemo, useState } from "react";

import Panel from "@/components/Panel";
import { listDocuments, processDocument, uploadDocument } from "@/lib/api";

export default function UploadCenterPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [statusLines, setStatusLines] = useState<string[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);

  const totalBytes = useMemo(() => files.reduce((sum, file) => sum + file.size, 0), [files]);

  const refresh = async () => {
    setDocuments(await listDocuments());
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const pushStatus = (line: string) => {
    setStatusLines((current) => [...current, line]);
  };

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const next = Array.from(incoming);
    if (!next.length) return;
    setFiles((current) => {
      const seen = new Set(current.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
      const unique = next.filter((file) => !seen.has(`${file.name}:${file.size}:${file.lastModified}`));
      return [...current, ...unique];
    });
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!files.length) return;
    setStatusLines([]);
    setProcessing(true);

    for (let index = 0; index < files.length; index += 1) {
      const file = files[index];
      const ordinal = `${index + 1}/${files.length}`;
      try {
        pushStatus(`[${ordinal}] Uploading ${file.name}...`);
        const doc = await uploadDocument(file);
        pushStatus(`[${ordinal}] Uploaded ${doc.original_filename}. Processing...`);
        const processed = await processDocument(doc.id);
        pushStatus(
          `[${ordinal}] Processed ${doc.original_filename} with ${processed.indexed_chunks} indexed chunks.`
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        pushStatus(`[${ordinal}] Failed ${file.name}: ${message}`);
      }
    }
    setProcessing(false);
    setFiles([]);
    await refresh();
  };

  return (
    <div className="space-y-4">
      <Panel title="Upload Center" subtitle="Drag-and-drop + multi-document upload with sequential processing.">
        <form className="space-y-3" onSubmit={submit}>
          <div
            className={`rounded-md border-2 border-dashed p-4 text-sm ${
              dragging ? "border-teal-700 bg-teal-50" : "border-slate-300 bg-white"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragging(false);
            }}
            onDrop={onDrop}
          >
            Drop medical documents here, or choose files below.
          </div>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
            multiple
            onChange={(event) => addFiles(event.target.files)}
            className="w-full rounded-md border p-2 text-sm"
          />
          <button className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white" type="submit" disabled={!files.length || processing}>
            {processing ? "Processing..." : `Upload and Process ${files.length ? `(${files.length})` : ""}`}
          </button>
          <p className="text-xs text-slate-600">
            Selected files: {files.length} • Total size: {(totalBytes / (1024 * 1024)).toFixed(2)} MB
          </p>
          {files.length ? (
            <ul className="max-h-40 space-y-1 overflow-auto rounded-md border p-2 text-xs">
              {files.map((file) => (
                <li key={`${file.name}:${file.size}:${file.lastModified}`} className="text-slate-700">
                  {file.name} • {(file.size / 1024).toFixed(1)} KB
                </li>
              ))}
            </ul>
          ) : null}
          {statusLines.length ? (
            <ul className="max-h-40 space-y-1 overflow-auto rounded-md border p-2 text-xs text-slate-700">
              {statusLines.map((line, idx) => (
                <li key={`${line}-${idx}`}>{line}</li>
              ))}
            </ul>
          ) : null}
        </form>
      </Panel>

      <Panel title="Recent Documents">
        <ul className="space-y-2 text-sm">
          {documents.map((doc) => (
            <li key={doc.id} className="rounded-md border p-2">
              <div className="font-medium">{doc.original_filename}</div>
              <div className="text-slate-500">Type: {doc.file_type} • Status: {doc.status}</div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
