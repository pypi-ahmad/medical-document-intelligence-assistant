"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { listAgentRuns } from "@/lib/api";

export default function AgentActivityPage() {
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    listAgentRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  return (
    <Panel title="Agent Activity" subtitle="Supervisor and specialized agent execution traces.">
      <ul className="space-y-2 text-sm">
        {runs.map((run) => (
          <li key={run.id} className="rounded border p-2">
            <div className="font-medium">{run.workflow} • {run.status}</div>
            <div className="text-xs text-slate-500">Started {new Date(run.started_at).toLocaleString()}</div>
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-100 p-2 text-xs dark:bg-slate-900">{JSON.stringify(run.trace_json, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
