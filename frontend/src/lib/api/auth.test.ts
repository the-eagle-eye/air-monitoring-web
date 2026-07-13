import { login, refresh, fetchMe } from './auth';

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
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('login', () => {
  it('POSTs email + password as JSON and returns the parsed body', async () => {
    mockFetchOnce({ jsonData: { access_token: 'tok' } });
    await expect(login('a@x.com', 'pw')).resolves.toEqual({
      access_token: 'tok',
    });
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/auth\/login$/);
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(opts.body)).toEqual({ email: 'a@x.com', password: 'pw' });
  });

  it('propagates the detail message when the server rejects', async () => {
    mockFetchOnce({
      ok: false,
      status: 401,
      jsonData: { detail: 'Credenciales invalidas' },
    });
    await expect(login('a@x.com', 'pw')).rejects.toThrow(
      'Credenciales invalidas',
    );
  });

  it('falls back to the generic message when there is no detail', async () => {
    mockFetchOnce({ ok: false, status: 500, jsonData: {} });
    await expect(login('a@x.com', 'pw')).rejects.toThrow(
      'Error al iniciar sesion',
    );
  });

  it('tolerates a non-JSON error body', async () => {
    const json = jest.fn().mockRejectedValue(new Error('not json'));
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json,
    } as unknown as Response);
    await expect(login('a@x.com', 'pw')).rejects.toThrow(
      'Error al iniciar sesion',
    );
  });
});

describe('refresh', () => {
  it('POSTs the refresh token and returns the new access token', async () => {
    mockFetchOnce({ jsonData: { access_token: 'fresh' } });
    await expect(refresh('r-tok')).resolves.toEqual({ access_token: 'fresh' });
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/auth\/refresh$/);
    expect(JSON.parse(opts.body)).toEqual({ refresh_token: 'r-tok' });
  });

  it('throws a fixed message when the refresh token is rejected', async () => {
    mockFetchOnce({ ok: false, status: 401, jsonData: {} });
    await expect(refresh('bad')).rejects.toThrow('Refresh token invalido');
  });
});

describe('fetchMe', () => {
  it('sends the Bearer token and returns the user', async () => {
    mockFetchOnce({ jsonData: { id: 1, email: 'a@x.com' } });
    await expect(fetchMe('tok')).resolves.toEqual({
      id: 1,
      email: 'a@x.com',
    });
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/auth\/me$/);
    expect(opts.headers.Authorization).toBe('Bearer tok');
  });

  it('throws when the token is rejected', async () => {
    mockFetchOnce({ ok: false, status: 401, jsonData: {} });
    await expect(fetchMe('stale')).rejects.toThrow('Token invalido');
  });
});
