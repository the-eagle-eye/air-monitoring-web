import { apiFetch, SERVICE_URLS } from './api';

// jsdom provides window/localStorage. We stub fetch only.
//
// The 401 branch of apiFetch does `window.location.href = '/login'`. jsdom's
// window.location is non-configurable (can't be replaced) AND its href setter
// performs a real navigation, which jsdom leaves unimplemented — so the redirect
// string can't be captured, and the attempt prints a noisy
// "Not implemented: navigation" console.error. We therefore assert the redirect's
// observable side effects (token cleared + 'Unauthorized' thrown) and silence the
// expected jsdom navigation error for that one case.
function mockFetchOnce(res: Partial<Response> & { jsonData?: unknown }) {
  const json = jest.fn().mockResolvedValue(res.jsonData ?? {});
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: res.ok ?? true,
    status: res.status ?? 200,
    json,
  } as unknown as Response);
  return json;
}

beforeEach(() => {
  global.fetch = jest.fn();
  localStorage.clear();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('apiFetch', () => {
  it('defaults to the gateway service base URL', async () => {
    mockFetchOnce({ jsonData: { ok: true } });
    await apiFetch('/ping');
    expect(global.fetch).toHaveBeenCalledWith(
      `${SERVICE_URLS.gateway}/ping`,
      expect.any(Object),
    );
  });

  it('routes to the selected microservice base URL', async () => {
    mockFetchOnce({ jsonData: {} });
    await apiFetch('/readings', { service: 'iot' });
    expect(global.fetch).toHaveBeenCalledWith(
      `${SERVICE_URLS.iot}/readings`,
      expect.any(Object),
    );
  });

  it('attaches the Bearer token from localStorage', async () => {
    localStorage.setItem('token', 'abc123');
    mockFetchOnce({ jsonData: {} });
    await apiFetch('/me');
    const [, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(opts.headers['Authorization']).toBe('Bearer abc123');
  });

  it('omits Authorization when there is no token', async () => {
    mockFetchOnce({ jsonData: {} });
    await apiFetch('/public');
    const [, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(opts.headers['Authorization']).toBeUndefined();
  });

  it('sends Content-Type application/json by default', async () => {
    mockFetchOnce({ jsonData: {} });
    await apiFetch('/x');
    const [, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(opts.headers['Content-Type']).toBe('application/json');
  });

  it('returns the parsed JSON body on success', async () => {
    mockFetchOnce({ jsonData: { value: 42 } });
    await expect(apiFetch<{ value: number }>('/x')).resolves.toEqual({
      value: 42,
    });
  });

  it('on 401 clears the token, attempts a redirect, and throws Unauthorized', async () => {
    // Silence the expected jsdom "Not implemented: navigation" error triggered
    // by apiFetch setting window.location.href on the 401 path.
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    try {
      localStorage.setItem('token', 'stale');
      mockFetchOnce({ ok: false, status: 401 });
      await expect(apiFetch('/secure')).rejects.toThrow('Unauthorized');
      expect(localStorage.getItem('token')).toBeNull();
    } finally {
      errorSpy.mockRestore();
    }
  });

  it('propagates the error.detail message from a non-ok response', async () => {
    mockFetchOnce({
      ok: false,
      status: 400,
      jsonData: { detail: 'Campo X requerido' },
    });
    await expect(apiFetch('/x')).rejects.toThrow('Campo X requerido');
  });

  it('falls back to HTTP <status> when the error body has no detail', async () => {
    mockFetchOnce({ ok: false, status: 500, jsonData: {} });
    await expect(apiFetch('/x')).rejects.toThrow('HTTP 500');
  });
});
