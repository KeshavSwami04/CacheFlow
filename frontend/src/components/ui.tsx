import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  sublabel,
  accent = "ink",
}: {
  label: string;
  value: ReactNode;
  sublabel?: string;
  accent?: "ink" | "signal" | "miss" | "info";
}) {
  const accentClass = {
    ink: "text-ink",
    signal: "text-signal",
    miss: "text-miss",
    info: "text-info",
  }[accent];

  return (
    <div className="card p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 font-display text-3xl font-semibold ${accentClass}`}>{value}</p>
      {sublabel && <p className="mt-1 text-xs text-faint">{sublabel}</p>}
    </div>
  );
}

export function Badge({ tone, children }: { tone: "active" | "inactive" | "warn"; children: ReactNode }) {
  const styles = {
    active: "bg-signal/10 text-signal border-signal/20",
    inactive: "bg-faint/10 text-faint border-faint/20",
    warn: "bg-warn/10 text-warn border-warn/20",
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles}`}>
      {children}
    </span>
  );
}

export function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between border-t border-border px-5 py-3.5">
      <p className="text-xs text-muted">
        Page <span className="text-ink">{page}</span> of {totalPages}
      </p>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="rounded-md border border-border px-3 py-1.5 text-xs text-muted transition hover:border-signal/40 hover:text-ink disabled:opacity-40 disabled:hover:border-border disabled:hover:text-muted"
        >
          Previous
        </button>
        <button
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="rounded-md border border-border px-3 py-1.5 text-xs text-muted transition hover:border-signal/40 hover:text-ink disabled:opacity-40 disabled:hover:border-border disabled:hover:text-muted"
        >
          Next
        </button>
      </div>
    </div>
  );
}
