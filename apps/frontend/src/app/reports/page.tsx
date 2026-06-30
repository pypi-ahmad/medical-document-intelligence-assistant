"use client";

import { FormEvent, useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { generateReport, listDocuments } from "@/lib/api";

export default function ReportsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("Doctor Visit Preparation Report");
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => undefined);
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const generated = await generateReport(selected, title);
    setReport(generated);
  };

  return (
    <div className="space-y-4">
      <Panel title="Reports" subtitle="Generate doctor-visit report with glossary and discussion questions.">
        <form className="space-y-2" onSubmit={submit}>
          <input
            className="w-full rounded border px-2 py-1 text-sm text-black"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <select
            className="h-28 w-full rounded border p-2 text-sm text-black"
            multiple
            value={selected}
            onChange={(event) =>
              setSelected(Array.from(event.target.selectedOptions).map((option) => option.value))
            }
          >
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>{doc.original_filename}</option>
            ))}
          </select>
          <button className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white" type="submit">Generate Report</button>
        </form>
      </Panel>

      {report ? (
        <Panel title={report.title} subtitle="Informational only. Review with qualified clinicians.">
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap text-xs">{report.markdown}</pre>
          <p className="text-xs text-amber-700">{report.safety.disclaimer}</p>
        </Panel>
      ) : null}
    </div>
  );
}
