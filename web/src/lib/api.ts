const ACCESS_KEY = "blt.access";
const REFRESH_KEY = "blt.refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  fields?: Record<string, string[]>;

  constructor(message: string, status: number, fields?: Record<string, string[]>) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

async function toError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body: keep the status text.
  }
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") {
      return new ApiError(record.detail, response.status);
    }
    const fields = record as Record<string, string[]>;
    const first = Object.values(fields)[0];
    if (Array.isArray(first) && typeof first[0] === "string") {
      return new ApiError(first[0], response.status, fields);
    }
  }
  return new ApiError(response.statusText || "Falha na requisição.", response.status);
}

let refreshing: Promise<boolean> | null = null;

async function refreshAccess(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = tokens.refresh;
      if (!refresh) return false;
      const response = await fetch("/api/v1/auth/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!response.ok) {
        tokens.clear();
        return false;
      }
      const data = (await response.json()) as { access: string; refresh?: string };
      tokens.set(data.access, data.refresh);
      return true;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);

  const response = await fetch(`/api/v1${path}`, { ...init, headers });

  const isAuthPath = path.startsWith("/auth/");
  if (response.status === 401 && retry && !isAuthPath && tokens.refresh) {
    if (await refreshAccess()) return apiFetch<T>(path, init, false);
  }
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
