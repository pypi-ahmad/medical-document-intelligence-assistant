"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getOCRPages, listDocuments } from "@/lib/api";

export default function OCRViewerPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [pages, setPages] = useState<any[]>([]);

  useEffect(() => {
    listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs[0]) setSelected(docs[0].id);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selected) return;
    getOCRPages(selected).then(setPages).catch(() => setPages([]));
  }, [selected]);

  return (
    <Panel title="OCR Viewer" subtitle="Page-level OCR text, layout blocks, and confidence.">
      <select className="rounded border px-2 py-1 text-sm text-black" value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Select document</option>
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>{doc.original_filename}</option>
        ))}
      </select>
      <div className="space-y-3">
        {pages.map((page) => (
          <article key={page.page_number} className="rounded-md border p-3 text-sm">
            <header className="mb-2 flex items-center justify-between">
              <strong>Page {page.page_number}</strong>
              <span className="badge">confidence: {page.confidence ?? "n/a"}</span>
            </header>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs">{page.text}</pre>
          </article>
        ))}
      </div>
    </Panel>
  );
}
