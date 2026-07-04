"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogoMark } from "@/components/Logo";

const LINKS = [
  { href: "/", label: "Library" },
  { href: "/qa", label: "Evidence Q&A" },
  { href: "/reports", label: "Report Builder" },
  { href: "/benchmark", label: "Benchmark" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-rule bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-3">
          <LogoMark />
          <span className="flex flex-col leading-tight">
            <span className="text-base font-semibold tracking-tight text-ink">Mini-Doc</span>
            <span className="text-[10px] uppercase tracking-[0.22em] text-stone-400">
              audit-ready docs
            </span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={
                  "rounded-md px-3 py-1.5 text-sm transition-colors " +
                  (active
                    ? "bg-stone-900 text-white"
                    : "text-stone-600 hover:bg-stone-100 hover:text-stone-900")
                }
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
