import { FormEvent, useState } from "react";
import { ApiException } from "@/services/api";
import { urlsApi } from "@/services/domain";
import type { ShortUrl } from "@/types";

export function CreateUrlForm({ onCreated }: { onCreated: (url: ShortUrl) => void }) {
  const [targetUrl, setTargetUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await urlsApi.create({
        target_url: targetUrl,
        custom_alias: alias || undefined,
      });
      onCreated(created);
      setTargetUrl("");
      setAlias("");
      setExpanded(false);
    } catch (err) {
      setError(err instanceof ApiException ? err.message : "Couldn't create that link.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="card p-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          required
          type="text"
          placeholder="https://example.com/a-very-long-url-to-shorten"
          className="input-field flex-1"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
        />
        {expanded && (
          <input
            type="text"
            placeholder="custom-alias (optional)"
            className="input-field sm:w-48"
            value={alias}
            onChange={(e) => setAlias(e.target.value)}
          />
        )}
        <button type="submit" disabled={submitting} className="btn-primary shrink-0 sm:w-36">
          {submitting ? "Shortening…" : "Shorten link"}
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-muted hover:text-signal"
        >
          {expanded ? "Hide custom alias" : "Add custom alias"}
        </button>
        {error && <p className="text-xs text-miss">{error}</p>}
      </div>
    </form>
  );
}
