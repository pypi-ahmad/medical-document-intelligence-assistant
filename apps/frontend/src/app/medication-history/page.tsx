"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getMedications, listDocuments } from "@/lib/api";

export default function MedicationHistoryPage() {
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
    getMedications(selected).then(setItems).catch(() => setItems([]));
  }, [selected]);

  return (
    <Panel title="Medication History" subtitle="Detected medications and apparent start/stop mentions.">
      <select className="rounded border px-2 py-1 text-sm text-black" value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Select document</option>
        {documents.map((doc) => (
          <option key={doc.id} value={doc.id}>{doc.original_filename}</option>
        ))}
      </select>
      <ul className="space-y-2 text-sm">
        {items.map((item, idx) => (
          <li key={`${item.medication_name}-${idx}`} className="rounded border p-2">
            <div className="font-medium">{item.medication_name}</div>
            <div className="text-slate-500">{item.dosage ?? "N/A"} • {item.frequency ?? "N/A"} • {item.action}</div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
