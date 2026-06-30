"use client";

import { FormEvent, useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { listDocuments, timeline } from "@/lib/api";

export default function TimelinePage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [eventTypes, setEventTypes] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    listDocuments().then(setDocuments).catch(() => undefined);
  }, []);

  const load = async (event?: FormEvent) => {
    event?.preventDefault();
    const types = eventTypes
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const payload = await timeline(selected, types, {
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    });
    setEvents(payload.events);
  };

  return (
    <Panel title="Timeline" subtitle="Chronological view of visits, labs, medications, and events.">
      <form className="space-y-2" onSubmit={load}>
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
        <input
          className="w-full rounded border p-2 text-sm text-black"
          value={eventTypes}
          onChange={(event) => setEventTypes(event.target.value)}
          placeholder="Event types (comma-separated): lab_test,doctor_visit,medication_change"
        />
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs">
            Start date
            <input
              type="date"
              className="mt-1 w-full rounded border p-2 text-sm text-black"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label className="text-xs">
            End date
            <input
              type="date"
              className="mt-1 w-full rounded border p-2 text-sm text-black"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>
        </div>
        <button className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white" type="submit">Load Timeline</button>
      </form>

      <ol className="space-y-2 text-sm">
        {events.map((event) => (
          <li key={`${event.id}-${event.event_type}`} className="rounded border p-2">
            <div className="font-medium">{event.title}</div>
            <div className="text-slate-500">{event.event_date ?? "Unknown date"} • {event.event_type}</div>
            <p>{event.description}</p>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
