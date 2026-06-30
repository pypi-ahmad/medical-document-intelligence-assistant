"use client";

import { FormEvent, useEffect, useState } from "react";

import Panel from "@/components/Panel";
import { getModelConfig, updateModelConfig } from "@/lib/api";

export default function ModelManagerPage() {
  const [config, setConfig] = useState<any>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getModelConfig().then(setConfig).catch(() => undefined);
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config) return;
    const updated = await updateModelConfig(config);
    setConfig(updated);
    setStatus("Model routing config updated");
  };

  if (!config) {
    return <Panel title="Model Manager">Load model configuration...</Panel>;
  }

  return (
    <Panel title="Model Manager" subtitle="Policy-driven local model routing.">
      <form className="space-y-2" onSubmit={submit}>
        {[
          "default_chat_model",
          "fast_chat_model",
          "summary_model",
          "entity_model",
          "embedding_model",
          "translation_model",
        ].map((field) => (
          <label key={field} className="block text-sm">
            <span className="mb-1 block font-medium">{field}</span>
            <input
              className="w-full rounded border px-2 py-1 text-black"
              value={config[field] ?? ""}
              onChange={(event) => setConfig({ ...config, [field]: event.target.value })}
            />
          </label>
        ))}
        <button className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white" type="submit">Save Model Routing</button>
      </form>
      {status ? <p className="text-sm text-emerald-600">{status}</p> : null}
    </Panel>
  );
}
