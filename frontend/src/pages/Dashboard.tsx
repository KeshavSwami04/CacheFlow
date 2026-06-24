import { useEffect, useState } from "react";
import { CreateUrlForm } from "@/components/CreateUrlForm";
import { Pagination, StatCard } from "@/components/ui";
import { UrlRow } from "@/components/UrlRow";
import { analyticsApi, urlsApi } from "@/services/domain";
import type { ShortUrl, UserAnalyticsSummary } from "@/types";

const PAGE_SIZE = 8;

export default function DashboardPage() {
  const [items, setItems] = useState<ShortUrl[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<UserAnalyticsSummary | null>(null);

  const loadUrls = async (targetPage = page, targetSearch = search) => {
    setLoading(true);
    try {
      const res = await urlsApi.list({ page: targetPage, page_size: PAGE_SIZE, search: targetSearch || undefined });
      setItems(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    setSummary(await analyticsApi.summary());
  };

  useEffect(() => {
    loadUrls(1, search);
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  useEffect(() => {
    loadSummary();
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-7">
        <h1 className="font-display text-2xl font-semibold text-ink">Your links</h1>
        <p className="mt-1 text-sm text-muted">Shorten, track, and manage every link in one place.</p>
      </header>

      {summary && (
        <div className="mb-7 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <StatCard label="Total links" value={summary.total_urls} />
          <StatCard label="Total clicks" value={summary.total_clicks} accent="signal" />
          <StatCard label="Clicks today" value={summary.clicks_today} accent="info" />
        </div>
      )}

      <div className="mb-5">
        <CreateUrlForm
          onCreated={() => {
            loadUrls(1, search);
            loadSummary();
            setPage(1);
          }}
        />
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <input
            type="text"
            placeholder="Search by URL, code, alias, or title…"
            className="input-field max-w-xs"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <p className="text-xs text-muted">{total} link{total === 1 ? "" : "s"}</p>
        </div>

        {loading ? (
          <div className="px-5 py-10 text-center text-sm text-muted">Loading…</div>
        ) : items.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <p className="text-sm text-muted">
              {search ? "No links match your search." : "You haven't created any links yet — shorten your first one above."}
            </p>
          </div>
        ) : (
          items.map((url) => (
            <UrlRow
              key={url.id}
              url={url}
              onChanged={(updated) => {
                if (updated) {
                  setItems((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
                } else {
                  loadUrls(page, search);
                  setTotal((t) => t - 1);
                }
                loadSummary();
              }}
            />
          ))
        )}

        <Pagination
          page={page}
          totalPages={totalPages}
          onChange={(p) => {
            setPage(p);
            loadUrls(p, search);
          }}
        />
      </div>
    </div>
  );
}
