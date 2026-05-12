import { test, expect } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { IOT, ML, GW, EMPTY_LIST } from './helpers/constants';

const MOCK_EQUIPOS = [
  { device_id: 'T101', nombre: 'Analizador SO2 T101', tipo: 'SO2', ubicacion: 'Sala A', estado: 'activo' },
  { device_id: 'T102', nombre: 'Analizador H2S T102', tipo: 'H2S', ubicacion: 'Sala B', estado: 'activo' },
];

const MOCK_PREDICTIONS_PAGE = {
  items: [{ device_id: 'T101', failure_probability: 0.15, remaining_useful_life_days: 85, risk_level: 'baja' }],
  total: 1,
};

const MOCK_ALERTAS = {
  items: [{ id: 1, device_id: 'T102', nivel_riesgo: 'alta', descripcion: 'RUL critico', estado: 'activa', created_at: new Date().toISOString() }],
  total: 1,
};

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await injectFakeAuth(page, 'administrador');

    await page.route(`${IOT}/api/v1/iot/equipos`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPOS) }),
    );
    await page.route(`${ML}/api/v1/predictions/**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PREDICTIONS_PAGE) }),
    );
    await page.route(`${ML}/api/v1/alerts**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTAS) }),
    );
    await page.route(`${GW}/api/v1/incidencias**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_LIST) }),
    );
    await page.route(`${GW}/api/v1/calibraciones**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_LIST) }),
    );
    await page.route(`${IOT}/api/v1/iot/readings/**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_LIST) }),
    );

    await page.goto('/dashboard');
  });

  test('renders KPI cards with correct values', async ({ page }) => {
    await expect(page.getByText(/Total Equipos/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('2').first()).toBeVisible();
  });

  test('renders equipment grid with device cards', async ({ page }) => {
    await expect(page.getByText('T101').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('T102').first()).toBeVisible();
  });

  test('equipment card links to detail page', async ({ page }) => {
    await page.getByText('T101').first().waitFor({ timeout: 10_000 });
    await expect(page.locator('a[href*="/equipos/T101"]').first()).toBeVisible();
  });

  test('incidencias summary section is visible', async ({ page }) => {
    await expect(page.getByText(/Incidencias/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test('proximas calibraciones section is visible', async ({ page }) => {
    await expect(page.getByText(/Calibraciones/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test('header shows logged-in user and logout button', async ({ page }) => {
    await expect(page.getByText(/Test User|Admin/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: /Salir/i })).toBeVisible();
  });

  test('logout redirects to /login', async ({ page }) => {
    const logoutBtn = page.getByRole('button', { name: /Salir/i });
    await logoutBtn.waitFor({ timeout: 10_000 });
    await logoutBtn.click();
    await page.waitForURL('**/login', { timeout: 10_000 });
    expect(page.url()).toContain('/login');
  });
});
