import type { Metadata } from "next";
import { IBM_Plex_Sans, Space_Grotesk } from "next/font/google";

import AppFrame from "@/components/AppFrame";
import "./globals.css";

const headingFont = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-heading" });
const bodyFont = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Medical Document Intelligence Assistant",
  description: "Educational local AI platform for organizing and understanding medical documents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable}`}>
      <body className="font-[var(--font-body)]">
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
