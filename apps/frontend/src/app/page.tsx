"use client";

import { useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getSystemHealth, listDocuments } from "@/lib/api";

export default function DashboardPage() {
  const [docCount, setDocCount] = useState<number>(0);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [docs, sys] = await Promise.all([listDocuments(), getSystemHealth()]);
        setDocCount(docs.length);
        setHealth(sys);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      }
    };
    load();
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Platform Overview" subtitle="Local educational medical document assistant.">
        <p className="text-sm">Documents indexed: <strong>{docCount}</strong></p>
        <p className="text-sm">Safety mode: <span className="badge">Educational use only</span></p>
        <p className="text-sm">Disclaimer: This platform does not diagnose, prescribe, or recommend treatment.</p>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </Panel>

      <Panel title="Runtime Status" subtitle="GPU/Ollama/agent runtime snapshot.">
        {health ? (
          <ul className="space-y-1 text-sm">
            <li>Status: <strong>{health.status}</strong></li>
            <li>GPU available: <strong>{String(health.gpu_available)}</strong></li>
            <li>Ollama models: <strong>{health.ollama?.count ?? 0}</strong></li>
            <li>Active agents: <strong>{health.active_agent_runs ?? 0}</strong></li>
            <li>Process memory: <strong>{Number(health.memory_usage_mb || 0).toFixed(1)} MB</strong></li>
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Load monitoring endpoint to view system snapshot.</p>
        )}
      </Panel>
    </div>
  );
}
