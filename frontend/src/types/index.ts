export interface User {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ShortUrl {
  id: number;
  short_code: string;
  custom_alias: string | null;
  target_url: string;
  title: string | null;
  created_at: string;
  expires_at: string | null;
  is_active: boolean;
  total_clicks: number;
  short_url: string;
}

export interface UrlListResponse {
  items: ShortUrl[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DailyClickPoint {
  stat_date: string;
  click_count: number;
}

export interface TopUrlEntry {
  short_code: string;
  target_url: string;
  title: string | null;
  total_clicks: number;
}

export interface ReferrerStat {
  referrer: string;
  count: number;
}

export interface CountryStat {
  country_code: string;
  count: number;
}

export interface UserAnalyticsSummary {
  total_urls: number;
  total_clicks: number;
  clicks_today: number;
  top_urls: TopUrlEntry[];
  daily_clicks: DailyClickPoint[];
}

export interface UrlAnalyticsResponse {
  short_code: string;
  total_clicks: number;
  daily_clicks: DailyClickPoint[];
  top_referrers: ReferrerStat[];
  top_countries: CountryStat[];
}

export interface CacheMetrics {
  hits: number;
  misses: number;
  hit_rate: number;
}

export interface QueueMetrics {
  queue_depth: number;
  dlq_depth: number;
  processed_events: number;
}

export interface WorkerStatus {
  worker_id: string;
  last_heartbeat_seconds_ago: number;
  alive: boolean;
}

export interface SystemMetrics {
  cache: CacheMetrics;
  queue: QueueMetrics;
  workers: WorkerStatus[];
  db_pool_size: number;
  db_pool_checked_out: number;
}

export interface ApiError {
  detail: string | { msg: string; loc: (string | number)[] }[];
}
