"use client";

import { useEffect, useMemo, useState } from "react";

import type { Citation, OCRPage } from "@/lib/api";
import { getOCRPages } from "@/lib/api";

type HighlightRange = { start: number; end: number };

function computeHighlightRange(pageText: string, evidenceText: string): HighlightRange | null {
  const text = pageText ?? "";
  const evidence = evidenceText.trim();
  if (!text || !evidence) return null;

  const lowerText = text.toLowerCase();
  const lowerEvidence = evidence.toLowerCase();
  const exact = lowerText.indexOf(lowerEvidence);
  if (exact >= 0) {
    return { start: exact, end: exact + lowerEvidence.length };
  }

  const words = evidence.split(/\s+/).filter((word) => word.length > 2);
  const phrase = words.slice(0, Math.min(10, words.length)).join(" ").toLowerCase();
  if (phrase.length >= 12) {
    const phraseIndex = lowerText.indexOf(phrase);
    if (phraseIndex >= 0) {
      return { start: phraseIndex, end: phraseIndex + phrase.length };
    }
  }

  const longestWords = [...words].sort((a, b) => b.length - a.length);
  for (const word of longestWords) {
    if (word.length < 6) break;
    const index = lowerText.indexOf(word.toLowerCase());
    if (index >= 0) {
      return { start: index, end: index + word.length };
    }
  }

  return null;
}

function HighlightedText({
  text,
  highlight,
}: {
  text: string;
  highlight: HighlightRange | null;
}) {
  if (!highlight) {
    return <pre className="max-h-[460px] overflow-auto whitespace-pre-wrap text-xs leading-6">{text}</pre>;
  }

  const before = text.slice(0, highlight.start);
  const marked = text.slice(highlight.start, highlight.end);
  const after = text.slice(highlight.end);

  return (
    <pre className="max-h-[460px] overflow-auto whitespace-pre-wrap text-xs leading-6">
      {before}
      <mark className="rounded bg-amber-300/80 px-1 text-black">{marked}</mark>
      {after}
    </pre>
  );
}

export default function EvidenceViewer({ citations }: { citations: Citation[] }) {
  const documents = useMemo(() => {
    const map = new Map<string, string>();
    for (const citation of citations) {
      map.set(citation.document_id, citation.document_name);
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [citations]);

  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [selectedCitationIndex, setSelectedCitationIndex] = useState<number>(0);
  const [selectedPageNumber, setSelectedPageNumber] = useState<number>(1);
  const [pages, setPages] = useState<OCRPage[]>([]);
  const [loadingPages, setLoadingPages] = useState(false);
  const [pageError, setPageError] = useState("");

  useEffect(() => {
    if (!documents.length) {
      setSelectedDocumentId("");
      return;
    }
    setSelectedDocumentId((current) => {
      if (current && documents.some((document) => document.id === current)) return current;
      return documents[0]?.id ?? "";
    });
  }, [documents]);

  const filteredCitations = useMemo(
    () => citations.filter((citation) => citation.document_id === selectedDocumentId),
    [citations, selectedDocumentId],
  );

  useEffect(() => {
    if (!filteredCitations.length) {
      setSelectedCitationIndex(0);
      setSelectedPageNumber(1);
      return;
    }
    setSelectedCitationIndex(0);
    setSelectedPageNumber(filteredCitations[0]?.page_number ?? 1);
  }, [filteredCitations]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setPages([]);
      return;
    }

    let cancelled = false;
    setLoadingPages(true);
    setPageError("");
    getOCRPages(selectedDocumentId)
      .then((nextPages) => {
        if (cancelled) return;
        setPages(nextPages);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setPages([]);
        setPageError(error instanceof Error ? error.message : "Failed to load OCR pages.");
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingPages(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDocumentId]);

  const activeCitation = filteredCitations[selectedCitationIndex] ?? null;
  const activePage =
    pages.find((page) => page.page_number === selectedPageNumber) ??
    pages.find((page) => page.page_number === activeCitation?.page_number) ??
    pages[0] ??
    null;
  const activePageNumber = activePage?.page_number ?? selectedPageNumber;
  const layoutBlocks = (activePage?.layout_json as { blocks?: unknown[] } | undefined)?.blocks;
  const blockCount = Array.isArray(layoutBlocks) ? layoutBlocks.length : 0;
  const highlight = computeHighlightRange(activePage?.text ?? "", activeCitation?.evidence_text ?? "");
  const pageCount = pages.length;

  const goToPage = (nextPage: number) => {
    setSelectedPageNumber(nextPage);
    const citationIndex = filteredCitations.findIndex((citation) => citation.page_number === nextPage);
    if (citationIndex >= 0) {
      setSelectedCitationIndex(citationIndex);
    }
  };

  return (
    <div className="grid gap-3 xl:grid-cols-[320px_1fr]">
      <section className="card p-3">
        <header className="mb-3">
          <h3 className="font-semibold">Evidence References</h3>
          <p className="text-xs text-slate-500">Pick citation to synchronize page + OCR text.</p>
        </header>
        {documents.length > 1 ? (
          <select
            className="mb-3 w-full rounded border px-2 py-1 text-sm text-black"
            value={selectedDocumentId}
            onChange={(event) => setSelectedDocumentId(event.target.value)}
          >
            {documents.map((document) => (
              <option key={document.id} value={document.id}>
                {document.name}
              </option>
            ))}
          </select>
        ) : null}
        <div className="space-y-2">
          {filteredCitations.map((citation, index) => {
            const isActive = index === selectedCitationIndex;
            return (
              <button
                key={`${citation.chunk_id ?? "chunk"}-${index}`}
                type="button"
                onClick={() => {
                  setSelectedCitationIndex(index);
                  if (citation.page_number) setSelectedPageNumber(citation.page_number);
                }}
                className={`w-full rounded border p-2 text-left text-xs transition ${
                  isActive
                    ? "border-teal-500 bg-teal-50/80 dark:bg-teal-900/20"
                    : "border-slate-300 hover:border-teal-400 dark:border-slate-700"
                }`}
              >
                <div className="mb-1 font-medium">
                  Page {citation.page_number ?? "n/a"} {citation.chunk_id ? `• ${citation.chunk_id.slice(0, 8)}` : ""}
                </div>
                <div className="max-h-24 overflow-hidden text-slate-500">{citation.evidence_text}</div>
              </button>
            );
          })}
          {!filteredCitations.length ? (
            <p className="rounded border border-dashed p-3 text-xs text-slate-500">
              No citations for selected document.
            </p>
          ) : null}
        </div>
      </section>

      <section className="space-y-3">
        <article className="card p-3">
          <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-semibold">Document Viewer</h3>
              <p className="text-xs text-slate-500">Evidence highlighted from selected citation.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                className="rounded border px-2 py-1 disabled:opacity-40"
                disabled={activePageNumber <= 1}
                onClick={() => goToPage(Math.max(1, activePageNumber - 1))}
              >
                Prev
              </button>
              <span className="badge">
                Page {activePageNumber}
                {pageCount ? ` / ${pageCount}` : ""}
              </span>
              <button
                type="button"
                className="rounded border px-2 py-1 disabled:opacity-40"
                disabled={!pageCount || activePageNumber >= pageCount}
                onClick={() => goToPage(Math.min(pageCount, activePageNumber + 1))}
              >
                Next
              </button>
            </div>
          </header>
          {loadingPages ? <p className="text-xs text-slate-500">Loading OCR pages...</p> : null}
          {pageError ? <p className="text-xs text-rose-700">{pageError}</p> : null}
          {!loadingPages && !pageError && activePage ? (
            <HighlightedText text={activePage.text} highlight={highlight} />
          ) : null}
          {!loadingPages && !pageError && !activePage ? (
            <p className="text-xs text-slate-500">No OCR page found for current citation.</p>
          ) : null}
        </article>

        <article className="card p-3">
          <header className="mb-2">
            <h3 className="font-semibold">Synchronized OCR Pane</h3>
            <p className="text-xs text-slate-500">
              Same page as viewer. Confidence/layout metadata shown for verification.
            </p>
          </header>
          {activePage ? (
            <div className="space-y-2 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="badge">provider: {activePage.provider || "unknown"}</span>
                <span className="badge">
                  confidence: {activePage.confidence == null ? "n/a" : activePage.confidence.toFixed(3)}
                </span>
                <span className="badge">blocks: {blockCount}</span>
              </div>
              <pre className="max-h-[280px] overflow-auto whitespace-pre-wrap rounded border bg-slate-50 p-2 leading-6 dark:bg-slate-900">
                {activePage.text}
              </pre>
            </div>
          ) : (
            <p className="text-xs text-slate-500">OCR pane unavailable for selected citation.</p>
          )}
        </article>
      </section>
    </div>
  );
}
