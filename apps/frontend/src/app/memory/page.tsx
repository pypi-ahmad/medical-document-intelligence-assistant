"use client";

import { FormEvent, useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { clearMemory, createMemory, listMemory } from "@/lib/api";

export default function MemoryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [key, setKey] = useState("preferred_summary_length");
  const [value, setValue] = useState('{"length":"medium"}');

  const load = async () => {
    setItems(await listMemory());
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createMemory({
      memory_type: "preference",
      memory_key: key,
      memory_value: JSON.parse(value),
    });
    await load();
  };

  return (
    <div className="space-y-4">
      <Panel title="Memory" subtitle="Inspect and manage stored conversation/document preferences.">
        <form className="space-y-2" onSubmit={submit}>
          <input className="w-full rounded border px-2 py-1 text-sm text-black" value={key} onChange={(event) => setKey(event.target.value)} />
          <textarea className="h-20 w-full rounded border px-2 py-1 text-sm text-black" value={value} onChange={(event) => setValue(event.target.value)} />
          <div className="flex gap-2">
            <button className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white" type="submit">Add Memory</button>
            <button
              type="button"
              className="rounded bg-red-700 px-3 py-1.5 text-sm text-white"
              onClick={async () => {
                await clearMemory();
                await load();
              }}
            >
              Clear All
            </button>
          </div>
        </form>
      </Panel>

      <Panel title="Current Memory Entries">
        <ul className="space-y-2 text-sm">
          {items.map((item) => (
            <li key={item.id} className="rounded border p-2">
              <div className="font-medium">{item.memory_type} • {item.memory_key}</div>
              <pre className="text-xs">{JSON.stringify(item.memory_value, null, 2)}</pre>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
