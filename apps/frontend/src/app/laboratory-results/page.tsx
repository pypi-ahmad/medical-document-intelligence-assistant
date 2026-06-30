"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getLabs, listDocuments } from "@/lib/api";

export default function LaboratoryResultsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState("");
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs[0]) setSelected(docs[0].id);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selected) return;
    getLabs(selected).then(setItems).catch(() => setItems([]));
  }, [selected]);

  return (
    <Panel title="Laboratory Results" subtitle="Parsed lab values with reference-range flagging.">
      <select className="rounded border px-2 py-1 text-sm text-black" value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Select document</option>
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>{doc.original_filename}</option>
        ))}
      </select>
      <div className="overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-2">Test</th>
              <th className="py-2">Value</th>
              <th className="py-2">Ref Range</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={`${item.test_name}-${idx}`} className="border-b border-slate-200/60">
                <td className="py-2">{item.test_name}</td>
                <td className="py-2">{item.value_text} {item.unit ?? ""}</td>
                <td className="py-2">{item.reference_range ?? "N/A"}</td>
                <td className="py-2">
                  {item.is_out_of_range === null || item.is_out_of_range === undefined
                    ? "Unknown"
                    : item.is_out_of_range
                    ? "Outside"
                    : "Within"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
