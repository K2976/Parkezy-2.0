import { env } from '@/config/env';

/** Error shape returned by every backend endpoint: {"error": {code, message, details}}. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** Field-level messages from a 422 response, keyed by field name. */
  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as { field?: string; message?: string }[])
        .filter((d) => d.field && d.message)
        .map((d) => [d.field as string, d.message as string]),
    );
  }
}

export const NETWORK_ERROR = 'network_error';

/** What the client needs from the auth layer (dependency inversion: no import of auth here). */
export interface TokenSource {
  accessToken(): string | null;
  /** Obtain a fresh access token; returns null when the session is gone. */
  refresh(): Promise<string | null>;
  onSessionLost(): void;
}

type Options = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT';
  body?: unknown;
  query?: Record<string, string | number | boolean | string[] | null | undefined>;
  headers?: Record<string, string>;
  auth?: boolean;
  signal?: AbortSignal;
};

function buildQuery(query: Options['query']): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.append(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : '';
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const data = await response.json();
    const error = data?.error ?? {};
    return new ApiError(
      response.status,
      error.code ?? 'http_error',
      error.message ?? 'Request failed',
      error.details,
    );
  } catch {
    return new ApiError(response.status, 'http_error', `Request failed (${response.status})`);
  }
}

export class ApiClient {
  private tokens: TokenSource | null = null;
  private refreshing: Promise<string | null> | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs: number,
  ) {}

  attach(tokens: TokenSource | null) {
    this.tokens = tokens;
  }

  /** Concurrent 401s share one refresh call. */
  private refreshOnce(): Promise<string | null> {
    if (!this.tokens) return Promise.resolve(null);
    this.refreshing ??= this.tokens.refresh().finally(() => {
      this.refreshing = null;
    });
    return this.refreshing;
  }

  private async send(path: string, options: Options, token: string | null): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    options.signal?.addEventListener('abort', () => controller.abort());
    const headers: Record<string, string> = { Accept: 'application/json', ...options.headers };
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = `Bearer ${token}`;
    try {
      return await fetch(`${this.baseUrl}${path}${buildQuery(options.query)}`, {
        method: options.method ?? 'GET',
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError(0, NETWORK_ERROR, 'Can’t reach Parkezy. Check your connection and try again.');
    } finally {
      clearTimeout(timer);
    }
  }

  async request<T>(path: string, options: Options = {}): Promise<T> {
    const useAuth = options.auth ?? true;
    let token = useAuth ? (this.tokens?.accessToken() ?? null) : null;
    let response = await this.send(path, options, token);

    if (response.status === 401 && useAuth && this.tokens) {
      token = await this.refreshOnce();
      if (!token) {
        this.tokens.onSessionLost();
        throw await parseError(response);
      }
      response = await this.send(path, options, token);
      if (response.status === 401) this.tokens.onSessionLost();
    }
    if (!response.ok) throw await parseError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }
}

export const api = new ApiClient(env.apiUrl, env.apiTimeoutMs);

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong';
}
