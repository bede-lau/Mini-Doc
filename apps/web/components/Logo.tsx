"use client";

export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" role="img" aria-label="Mini-Doc logo">
      <defs>
        <linearGradient id="mini-doc-mark" x1="8" x2="40" y1="4" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0F766E" />
          <stop offset="0.55" stopColor="#0F172A" />
          <stop offset="1" stopColor="#B45309" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="14" fill="#F8FAFC" />
      <path
        d="M14 10.5h14.4L36 18.1v19.4H14V10.5Z"
        fill="white"
        stroke="url(#mini-doc-mark)"
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
      <path d="M28 11v8h8" fill="none" stroke="#0F766E" strokeWidth="2.4" strokeLinejoin="round" />
      <path d="M19 25h14M19 30h10" stroke="#0F172A" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M18 37.5 30 37.5" stroke="#B45309" strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}

