import { test, expect, type Page } from '@playwright/test';
import { GW, IOT, EMPTY_LIST } from './helpers/constants';

const AUTH_LOGIN = `${GW}/api/v1/auth/login`;
const AUTH_ME = `${GW}/api/v1/auth/me`;

const ADMIN_USER = {
  id: 1,
  email: 'admin@oefa.gob.pe',
  nombre: 'Admin',
  apellido: 'OEFA',
  rol: 'administrador',
};
const TECNICO_USER = {
  id: 2,
  email: 'tecnico1@oefa.gob.pe',
  nombre: 'Tecnico',
  apellido: 'OEFA',
  rol: 'tecnico',
};

const emailInput = (page: Page) => page.locator('input[type="email"]');
const passwordInput = (page: Page) => page.locator('input[type="password"]');

// page.route() MUST be registered before page.goto() so AuthProvider's
// mount-time /auth/me call is intercepted. No shared beforeEach goto here.

test.describe('Login flow', () => {
  test('renders login form with credential hints', async ({ page }) => {
    await page.route(AUTH_ME, (route) =>
      route.fulfill({ status: 401, body: '{}' }),
    );
    await page.goto('/login');

    await expect(
      page.getByRole('heading', { name: /Iniciar Sesion/i }),
    ).toBeVisible();
    await expect(emailInput(page)).toBeVisible();
    await expect(passwordInput(page)).toBeVisible();
    await expect(page.getByRole('button', { name: /Ingresar/i })).toBeVisible();
    await expect(page.getByText('admin@oefa.gob.pe').first()).toBeVisible();
  });

  test('shows error on wrong credentials', async ({ page }) => {
    await page.route(AUTH_ME, (route) =>
      route.fulfill({ status: 401, body: '{}' }),
    );
    await page.route(AUTH_LOGIN, (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Credenciales incorrectas' }),
      }),
    );
    await page.goto('/login');

    await emailInput(page).fill('wrong@oefa.gob.pe');
    await passwordInput(page).fill('badpassword');
    await page.getByRole('button', { name: /Ingresar/i }).click();

    await expect(page.getByText('Credenciales incorrectas')).toBeVisible({
      timeout: 10_000,
    });
    expect(page.url()).toContain('/login');
  });

  test('shows loading state while submitting', async ({ page }) => {
    await page.route(AUTH_ME, (route) =>
      route.fulfill({ status: 401, body: '{}' }),
    );
    await page.route(AUTH_LOGIN, async (route) => {
      await new Promise((r) => setTimeout(r, 600));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'tok',
          refresh_token: 'ref',
          usuario: ADMIN_USER,
        }),
      });
    });
    await page.goto('/login');

    await emailInput(page).fill('admin@oefa.gob.pe');
    await passwordInput(page).fill('admin123');
    await page.getByRole('button', { name: /Ingresar/i }).click();

    await expect(
      page.getByRole('button', { name: /Ingresando.../i }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test('admin login redirects to /dashboard', async ({ page }) => {
    await page.route(AUTH_LOGIN, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          usuario: ADMIN_USER,
        }),
      }),
    );
    await page.route(AUTH_ME, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ADMIN_USER),
      }),
    );
    await page.goto('/login');

    await emailInput(page).fill('admin@oefa.gob.pe');
    await passwordInput(page).fill('admin123');
    await page.getByRole('button', { name: /Ingresar/i }).click();

    await page.waitForURL('**/dashboard', { timeout: 10_000 });
    expect(page.url()).toContain('/dashboard');
  });

  test('tecnico login redirects to /dashboard-tecnico', async ({ page }) => {
    // Mock all API calls the tecnico dashboard page makes so there are no unhandled network errors
    await page.route(`${GW}/api/v1/incidencias**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_LIST),
      }),
    );
    await page.route(`${IOT}/api/v1/iot/equipos`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      }),
    );
    await page.route(`${GW}/api/v1/repuestos`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      }),
    );
    await page.route(AUTH_LOGIN, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-token-tecnico',
          refresh_token: 'mock-refresh-tecnico',
          usuario: TECNICO_USER,
        }),
      }),
    );
    await page.route(AUTH_ME, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(TECNICO_USER),
      }),
    );
    await page.goto('/login');

    await emailInput(page).fill('tecnico1@oefa.gob.pe');
    await passwordInput(page).fill('tecnico123');
    await page.getByRole('button', { name: /Ingresar/i }).click();

    await page.waitForURL('**/dashboard-tecnico', { timeout: 10_000 });
    expect(page.url()).toContain('/dashboard-tecnico');
  });

  test('unauthenticated user is redirected to /login', async ({ page }) => {
    await page.route(AUTH_ME, (route) =>
      route.fulfill({ status: 401, body: '{}' }),
    );
    // Don't wait for load — AuthProvider aborts the /dashboard nav with router.replace('/login').
    await page.goto('/dashboard', { waitUntil: 'commit' }).catch((e: Error) => {
      if (!e.message.includes('navigation')) throw e;
    });
    await expect
      .poll(() => new URL(page.url()).pathname, { timeout: 10_000 })
      .toBe('/login');
  });
});
