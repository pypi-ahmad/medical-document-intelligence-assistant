"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { listDocuments, processDocument } from "@/lib/api";

export default function MedicalDocumentsPage() {
  const [docs, setDocs] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("");

  const load = async () => {
    setDocs(await listDocuments());
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <Panel title="Medical Documents" subtitle="Manage uploaded records and rerun processing.">
      <ul className="space-y-2">
        {docs.map((doc) => (
          <li key={doc.id} className="card flex items-center justify-between px-3 py-2 text-sm">
            <div>
              <div className="font-medium">{doc.original_filename}</div>
              <div className="text-slate-500">{doc.file_type} • {Math.round(doc.file_size / 1024)} KB</div>
            </div>
            <button
              className="rounded-md bg-slate-800 px-3 py-1.5 text-xs text-white"
              onClick={async () => {
                setStatus(`Processing ${doc.original_filename}...`);
                await processDocument(doc.id);
                setStatus(`Completed ${doc.original_filename}`);
              }}
            >
              Reprocess
            </button>
          </li>
        ))}
      </ul>
      {status ? <p className="text-sm text-slate-600">{status}</p> : null}
    </Panel>
  );
}
