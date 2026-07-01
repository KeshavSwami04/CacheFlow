import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui";
import { urlsApi } from "@/services/domain";
import type { ShortUrl } from "@/types";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function UrlRow({
  url,
  onChanged,
}: {
  url: ShortUrl;
  onChanged: (updated: ShortUrl | null) => void;
}) {
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const copy = async () => {
    try {
      let copySuccess = false;
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        try {
          await navigator.clipboard.writeText(url.short_url);
          copySuccess = true;
        } catch (err) {
          console.warn("navigator.clipboard.writeText failed, trying fallback...", err);
        }
      }

      if (!copySuccess) {
        const textArea = document.createElement("textarea");
        textArea.value = url.short_url;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          copySuccess = document.execCommand("copy");
        } catch (err) {
          console.error("execCommand copy failed", err);
        } finally {
          document.body.removeChild(textArea);
        }
      }

      if (copySuccess) {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }
    } catch (err) {
      console.error("Failed to copy link: ", err);
    }
  };

  const toggleActive = async () => {
    setBusy(true);
    try {
      const updated = await urlsApi.update(url.id, { is_active: !url.is_active });
      onChanged(updated);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm("Delete this link permanently? This can't be undone.")) return;
    setBusy(true);
    try {
      await urlsApi.remove(url.id);
      onChanged(null);
    } finally {
      setBusy(false);
    }
  };

  const isExpired = url.expires_at && new Date(url.expires_at) <= new Date();

  return (
    <div className="flex flex-col gap-3 border-b border-border px-5 py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link
            to={`/dashboard/urls/${url.id}`}
            className="truncate font-mono text-sm font-medium text-signal hover:underline"
          >
            {url.short_url.replace(/^https?:\/\//, "")}
          </Link>
          <button onClick={copy} className="shrink-0 text-xs text-faint hover:text-ink" title="Copy link">
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <p className="mt-0.5 truncate text-sm text-muted" title={url.target_url}>
          {url.target_url}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {!url.is_active ? (
            <Badge tone="inactive">Deactivated</Badge>
          ) : isExpired ? (
            <Badge tone="warn">Expired</Badge>
          ) : (
            <Badge tone="active">Active</Badge>
          )}
          <span className="text-xs text-faint">Created {formatDate(url.created_at)}</span>
        </div>
      </div>

      <div className="flex items-center gap-5 sm:gap-6">
        <div className="text-right">
          <p className="font-display text-lg font-semibold text-ink">{url.total_clicks}</p>
          <p className="text-xs text-faint">clicks</p>
        </div>
        <div className="flex gap-1.5">
          <button
            disabled={busy}
            onClick={toggleActive}
            className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted transition hover:border-signal/40 hover:text-ink disabled:opacity-50"
          >
            {url.is_active ? "Deactivate" : "Activate"}
          </button>
          <button
            disabled={busy}
            onClick={remove}
            className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted transition hover:border-miss/40 hover:text-miss disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
