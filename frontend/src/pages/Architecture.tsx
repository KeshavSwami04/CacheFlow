import { useEffect, useRef, useState } from "react";
import { SystemFlowDiagram } from "@/components/SystemFlowDiagram";
import { StatCard } from "@/components/ui";
import { architectureApi } from "@/services/domain";
import type { SystemMetrics } from "@/types";

const POLL_INTERVAL_MS = 4000;

export default function ArchitecturePage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await architectureApi.metrics();
        setMetrics(data);
        setLastUpdated(new Date());
        setError(false);
      } catch {
        setError(true);
      }
    };
    poll();
    timer.current = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-7 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Architecture</h1>
          <p className="mt-1 text-sm text-muted">
            Live internals of the system serving this app — not a screenshot.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-faint">
          <span className={`h-1.5 w-1.5 rounded-full ${error ? "bg-miss" : "bg-signal animate-pulse_dot"}`} />
          {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Connecting…"}
        </div>
      </header>

      {!metrics ? (
        <div className="card px-5 py-10 text-center text-sm text-muted">
          {error ? "Couldn't reach the metrics endpoint. Retrying…" : "Loading live metrics…"}
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard
              label="Cache hit rate"
              value={`${Math.round(metrics.cache.hit_rate * 100)}%`}
              sublabel={`${metrics.cache.hits} hits`}
              accent="signal"
            />
            <StatCard label="Cache misses" value={metrics.cache.misses} accent="miss" />
            <StatCard label="Queue depth" value={metrics.queue.queue_depth} accent="info" sublabel="click_events.process" />
            <StatCard
              label="DLQ count"
              value={metrics.queue.dlq_depth}
              accent={metrics.queue.dlq_depth > 0 ? "miss" : "ink"}
              sublabel="dead-lettered after 3 retries"
            />
          </div>

          <div className="mb-6">
            <SystemFlowDiagram metrics={metrics} />
          </div>

          <div className="mb-6 grid gap-6 sm:grid-cols-2">
            <div className="card p-5">
              <h2 className="mb-4 text-sm font-medium text-ink">Worker fleet</h2>
              {metrics.workers.length === 0 ? (
                <p className="text-sm text-muted">No worker heartbeats seen yet.</p>
              ) : (
                <ul className="space-y-3">
                  {metrics.workers.map((w) => (
                    <li key={w.worker_id} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 font-mono text-xs text-muted">
                        <span className={`h-1.5 w-1.5 rounded-full ${w.alive ? "bg-signal" : "bg-miss"}`} />
                        {w.worker_id}
                      </span>
                      <span className="text-xs text-faint">
                        {w.alive ? "alive" : "stale"} · {w.last_heartbeat_seconds_ago}s ago
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-4 text-xs text-faint">
                {metrics.queue.processed_events.toLocaleString()} events processed since the worker pool
                last restarted.
              </p>
            </div>

            <div className="card p-5">
              <h2 className="mb-4 text-sm font-medium text-ink">DB connection pool</h2>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-muted">In use</span>
                <span className="font-mono text-ink">
                  {metrics.db_pool_checked_out} / {metrics.db_pool_size}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-bg">
                <div
                  className="h-full rounded-full bg-info"
                  style={{ width: `${(metrics.db_pool_checked_out / Math.max(1, metrics.db_pool_size)) * 100}%` }}
                />
              </div>
              <p className="mt-4 text-xs text-faint">
                This is per API replica. With N replicas behind the load balancer, total Postgres
                connections ≈ N × pool size — the number to size <code className="font-mono">max_connections</code> against.
              </p>
            </div>
          </div>

          <ScalingNotes />
        </>
      )}
    </div>
  );
}

function ScalingNotes() {
  return (
    <div className="card p-5">
      <h2 className="mb-3 text-sm font-medium text-ink">Scalability notes</h2>
      <div className="grid gap-4 text-sm text-muted sm:grid-cols-2">
        <p>
          <span className="font-medium text-ink">Stateless API tier.</span> JWT auth means no
          server-side session — any replica can serve any request, so the API scales horizontally by
          simply adding replicas behind a load balancer.
        </p>
        <p>
          <span className="font-medium text-ink">Independent worker scaling.</span> Workers are
          competing consumers on the same queue. Click-traffic spikes are absorbed by scaling worker
          replicas without touching the API tier.
        </p>
        <p>
          <span className="font-medium text-ink">Cache-aside reads.</span> The redirect hot path is
          cache-only in the common case — no DB hit, no synchronous queue wait — keeping p99 redirect
          latency low under load.
        </p>
        <p>
          <span className="font-medium text-ink">Future: Postgres read replicas.</span> Analytics and
          dashboard list queries are read-heavy and tolerate slight staleness — good candidates to route
          to read replicas once query volume justifies the operational cost. See System Design Decisions.
        </p>
      </div>
    </div>
  );
}
