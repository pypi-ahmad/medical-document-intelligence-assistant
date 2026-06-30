"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getSystemHealth } from "@/lib/api";

export default function SystemMonitoringPage() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      const payload = await getSystemHealth();
      setHealth(payload);
    };
    load().catch(() => undefined);
    const interval = setInterval(() => {
      load().catch(() => undefined);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Panel title="System Monitoring" subtitle="GPU, memory, Ollama status, active agent executions.">
      {health ? (
        <pre className="max-h-[520px] overflow-auto rounded bg-slate-100 p-3 text-xs dark:bg-slate-900">{JSON.stringify(health, null, 2)}</pre>
      ) : (
        <p className="text-sm text-slate-500">Loading health telemetry...</p>
      )}
    </Panel>
  );
}
