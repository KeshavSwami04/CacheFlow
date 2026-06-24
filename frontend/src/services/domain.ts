import { api } from "@/services/api";
import type {
  AuthTokens,
  ShortUrl,
  SystemMetrics,
  UrlAnalyticsResponse,
  UrlListResponse,
  User,
  UserAnalyticsSummary,
} from "@/types";

export const authApi = {
  signup: (email: string, password: string, full_name?: string) =>
    api.post<AuthTokens>("/api/v1/auth/signup", { email, password, full_name }),
  login: (email: string, password: string) =>
    api.post<AuthTokens>("/api/v1/auth/login", { email, password }),
  me: () => api.get<User>("/api/v1/auth/me"),
};

export interface CreateUrlPayload {
  target_url: string;
  custom_alias?: string;
  expires_at?: string;
  title?: string;
}

export interface UpdateUrlPayload {
  target_url?: string;
  expires_at?: string | null;
  is_active?: boolean;
  title?: string;
}

export const urlsApi = {
  list: (params: { page?: number; page_size?: number; search?: string; is_active?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.search) qs.set("search", params.search);
    if (params.is_active !== undefined) qs.set("is_active", String(params.is_active));
    return api.get<UrlListResponse>(`/api/v1/urls?${qs.toString()}`);
  },
  create: (payload: CreateUrlPayload) => api.post<ShortUrl>("/api/v1/urls", payload),
  update: (id: number, payload: UpdateUrlPayload) => api.patch<ShortUrl>(`/api/v1/urls/${id}`, payload),
  remove: (id: number) => api.delete<void>(`/api/v1/urls/${id}`),
};

export const analyticsApi = {
  summary: () => api.get<UserAnalyticsSummary>("/api/v1/analytics/summary"),
  forUrl: (id: number, days = 30) => api.get<UrlAnalyticsResponse>(`/api/v1/analytics/urls/${id}?days=${days}`),
};

export const architectureApi = {
  metrics: () => api.get<SystemMetrics>("/api/v1/architecture/metrics"),
};
