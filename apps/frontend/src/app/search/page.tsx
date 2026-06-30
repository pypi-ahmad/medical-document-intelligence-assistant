"use client";

import { FormEvent, useState } from "react";

import Panel from "@/components/Panel";
import { search } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("medication changes");
  const [results, setResults] = useState<any[]>([]);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [minScore, setMinScore] = useState("0.05");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsedMinScore = Number(minScore);
    const filters = Number.isFinite(parsedMinScore) ? { min_score: parsedMinScore } : {};
    const payload = await search(query, [], {
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      filters,
    });
    setResults(payload.results);
    setDiagnostics(payload.diagnostics ?? null);
  };

  return (
    <Panel title="Search" subtitle="Hybrid semantic + keyword retrieval over indexed chunks.">
      <form className="space-y-2" onSubmit={submit}>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border px-2 py-1 text-sm text-black"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white" type="submit">Search</button>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="text-xs">
            Start date
            <input
              type="date"
              className="mt-1 w-full rounded border px-2 py-1 text-sm text-black"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label className="text-xs">
            End date
            <input
              type="date"
              className="mt-1 w-full rounded border px-2 py-1 text-sm text-black"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>
          <label className="text-xs">
            Min score
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              className="mt-1 w-full rounded border px-2 py-1 text-sm text-black"
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
            />
          </label>
        </div>
      </form>
      {diagnostics ? (
        <pre className="rounded border bg-slate-100 p-2 text-xs dark:bg-slate-900">
          {JSON.stringify(diagnostics, null, 2)}
        </pre>
      ) : null}
      <ul className="space-y-2 text-sm">
        {results.map((result) => (
          <li key={result.chunk_id} className="rounded border p-2">
            <div className="font-medium">{result.document_name} • page {result.page_number ?? "n/a"}</div>
            <div className="text-xs text-slate-500">score {result.score.toFixed(3)} | semantic {result.semantic_score.toFixed(3)} | keyword {result.keyword_score.toFixed(3)}</div>
            <p>{result.text}</p>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
