const API_GATEWAY_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000';
const IOT_SERVICE_URL =
  process.env.NEXT_PUBLIC_IOT_SERVICE_URL || 'http://localhost:8001';
const ML_SERVICE_URL =
  process.env.NEXT_PUBLIC_ML_SERVICE_URL || 'http://localhost:8002';
const OPS_SERVICE_URL =
  process.env.NEXT_PUBLIC_OPS_SERVICE_URL || 'http://localhost:8003';

export const SERVICE_URLS = {
  gateway: API_GATEWAY_URL,
  iot: IOT_SERVICE_URL,
  ml: ML_SERVICE_URL,
  ops: OPS_SERVICE_URL,
} as const;

type ServiceName = keyof typeof SERVICE_URLS;

interface FetchOptions extends RequestInit {
  service?: ServiceName;
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { service = 'gateway', ...fetchOptions } = options;
  const baseUrl = SERVICE_URLS[service];

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string>),
  };

  const token =
    typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
