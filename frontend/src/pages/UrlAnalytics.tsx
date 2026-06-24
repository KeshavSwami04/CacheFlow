import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { StatCard } from "@/components/ui";
import { analyticsApi } from "@/services/domain";
import type { UrlAnalyticsResponse } from "@/types";

export default function UrlAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<UrlAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    analyticsApi
      .forUrl(Number(id))
      .then(setData)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="px-1 py-10 text-sm text-muted">Loading analytics…</div>;
  }
  if (!data) {
    return <div className="px-1 py-10 text-sm text-muted">No data found for this link.</div>;
  }

  const chartData = data.daily_clicks.map((d) => ({ date: d.stat_date.slice(5), clicks: d.click_count }));

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/dashboard" className="text-xs text-muted hover:text-signal">
        ← Back to links
      </Link>
      <header className="mb-7 mt-2">
        <h1 className="font-mono text-xl font-semibold text-signal">/{data.short_code}</h1>
        <p className="mt-1 text-sm text-muted">Click analytics for the last 30 days</p>
      </header>

      <div className="mb-7 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard label="Total clicks" value={data.total_clicks} accent="signal" />
        <StatCard label="Top referrer" value={data.top_referrers[0]?.referrer ?? "direct"} />
        <StatCard label="Top country" value={data.top_countries[0]?.country_code ?? "—"} />
      </div>

      <div className="card mb-6 p-5">
        <h2 className="mb-4 text-sm font-medium text-ink">Clicks per day</h2>
        {chartData.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No clicks recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2832" vertical={false} />
              <XAxis dataKey="date" stroke="#5C6876" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#5C6876" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: "#11161D", border: "1px solid #1F2832", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#E7EDF3" }}
              />
              <Bar dataKey="clicks" fill="#27E6A6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <BreakdownCard title="Top referrers" rows={data.top_referrers.map((r) => ({ label: r.referrer, count: r.count }))} />
        <BreakdownCard title="Top countries (mocked)" rows={data.top_countries.map((c) => ({ label: c.country_code, count: c.count }))} />
      </div>
    </div>
  );
}

function BreakdownCard({ title, rows }: { title: string; rows: { label: string; count: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div className="card p-5">
      <h2 className="mb-4 text-sm font-medium text-ink">{title}</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">No data yet.</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.label}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-mono text-muted">{row.label}</span>
                <span className="text-ink">{row.count}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-bg">
                <div
                  className="h-full rounded-full bg-signal/70"
                  style={{ width: `${(row.count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
