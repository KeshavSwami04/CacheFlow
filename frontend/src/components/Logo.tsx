export function LogoMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="0.5" y="0.5" width="23" height="23" rx="6" stroke="#27E6A6" strokeOpacity="0.35" />
      <path
        d="M5 16 Q 9 8, 12 12 T 19 8"
        stroke="#27E6A6"
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
        strokeDasharray="3 3"
        className="animate-flow"
      />
      <circle cx="19" cy="8" r="1.6" fill="#27E6A6" className="animate-pulse_dot" />
    </svg>
  );
}

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2">
      <LogoMark size={size} />
      <span className="font-display text-base font-semibold tracking-tight text-ink">
        Cache<span className="text-signal">Flow</span>
      </span>
    </div>
  );
}
