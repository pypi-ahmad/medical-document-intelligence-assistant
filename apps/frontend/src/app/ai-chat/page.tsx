"use client";

import { FormEvent, useState } from "react";

import EvidenceViewer from "@/components/EvidenceViewer";
import Panel from "@/components/Panel";
import { QAResult, streamQuestion } from "@/lib/api";

export default function AIChatPage() {
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<QAResult | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [streamModel, setStreamModel] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    setResult(null);
    setStreamingAnswer("");
    setStreamModel("");
    try {
      const response = await streamQuestion(question, sessionId, [], {
        onSession: (payload) => {
          setSessionId(payload.session_id);
          setStreamModel(payload.model);
        },
        onToken: (token) => {
          setStreamingAnswer((current) => current + token);
        },
        onDone: (payload) => {
          setResult({
            session_id: payload.session_id,
            answer: payload.answer,
            extracted_information: "",
            educational_background: "",
            citations: payload.citations,
            safety: payload.safety,
            model: payload.model,
          });
        },
        onError: (message) => {
          setError(message);
        },
      });
      setSessionId(response.session_id);
      setQuestion("");
      setStreamingAnswer("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to stream response.";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <Panel title="AI Chat" subtitle="Grounded answers with evidence citations.">
        <form className="space-y-2" onSubmit={submit}>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="h-24 w-full rounded-md border p-2 text-sm text-black"
            placeholder="Ask about medications, labs, timeline, or terminology..."
          />
          <button className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white" disabled={busy}>
            {busy ? "Thinking..." : "Ask"}
          </button>
        </form>
        {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      </Panel>

      {busy && streamingAnswer ? (
        <Panel title="Streaming Answer" subtitle={`Model: ${streamModel || "routing..."}`}>
          <p className="text-sm whitespace-pre-wrap">{streamingAnswer}</p>
        </Panel>
      ) : null}

      {result ? (
        <Panel title="Answer" subtitle={`Model: ${result.model}`}>
          <p className="text-sm whitespace-pre-wrap">{result.answer}</p>
          <h3 className="text-sm font-semibold">Evidence</h3>
          <EvidenceViewer citations={result.citations} />
          <p className="text-xs text-amber-700">{result.safety.disclaimer}</p>
        </Panel>
      ) : null}
    </div>
  );
}
