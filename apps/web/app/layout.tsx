import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "EvidenceOS Mini",
  description: "Audit-ready document intelligence for regulated workflows.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <Nav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-6 text-[11px] text-stone-400">
          EvidenceOS Mini — public demo data only. Not legal, financial, insurance, or regulatory advice.
        </footer>
      </body>
    </html>
  );
}
