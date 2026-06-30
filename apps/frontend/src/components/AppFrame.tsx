"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import AuthPanel from "@/components/AuthPanel";
import ThemeToggle from "@/components/ThemeToggle";

const NAV_ITEMS = [
  ["Dashboard", "/"],
  ["Upload Center", "/upload-center"],
  ["Medical Documents", "/medical-documents"],
  ["AI Chat", "/ai-chat"],
  ["OCR Viewer", "/ocr-viewer"],
  ["Timeline", "/timeline"],
  ["Medication History", "/medication-history"],
  ["Laboratory Results", "/laboratory-results"],
  ["Reports", "/reports"],
  ["Search", "/search"],
  ["Memory", "/memory"],
  ["Agent Activity", "/agent-activity"],
  ["Settings", "/settings"],
  ["Model Manager", "/model-manager"],
  ["System Monitoring", "/system-monitoring"],
] as const;

export default function AppFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-300/60 bg-white/70 px-4 py-3 backdrop-blur dark:bg-slate-900/60 dark:border-slate-700/70">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Medical Document Intelligence Assistant</h1>
            <p className="text-xs text-slate-500">Educational-use medical document understanding platform (local-first).</p>
          </div>
          <div className="flex items-center gap-2">
            <AuthPanel />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1400px] grid-cols-1 gap-4 px-4 py-4 md:grid-cols-[260px_1fr]">
        <aside className="card max-h-[calc(100vh-140px)] overflow-auto p-2">
          <nav className="space-y-1">
            {NAV_ITEMS.map(([label, href]) => (
              <Link
                key={href}
                href={href}
                className={`block rounded-md px-3 py-2 text-sm transition ${pathname === href ? "nav-link-active" : "hover:bg-slate-200/70 dark:hover:bg-slate-700/60"}`}
              >
                {label}
              </Link>
            ))}
          </nav>
        </aside>

        <main className="fade-slide">{children}</main>
      </div>
    </div>
  );
}
