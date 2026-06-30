import type { ReactNode } from "react";

export default function Panel({ title, children, subtitle }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="card p-4">
      <header className="mb-3 border-b border-slate-200 pb-2 dark:border-slate-700">
        <h2 className="font-[var(--font-heading)] text-lg font-semibold">{title}</h2>
        {subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}
      </header>
      <div className="space-y-3">{children}</div>
    </section>
  );
}
