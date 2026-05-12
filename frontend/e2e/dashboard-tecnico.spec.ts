import { test, expect } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { IOT, GW, ML, EMPTY_LIST } from './helpers/constants';

const MOCK_INCIDENCIAS_PENDIENTES = {
  items: [
    {
      id: 10,
      device_id: 'T103',
      tipo: 'correctiva',
      descripcion: 'Sensor SO2 fuera de rango',
      estado: 'pendiente',
      prioridad: 'alta',
      responsable_id: 2,
      mantenimiento_correctivo: null,
      created_at: new Date().toISOString(),
      updated_at: null,
    },
  ],
  total: 1,
};

const MOCK_EQUIPOS = [
  { device_id: 'T103', nombre: 'Analizador SO2 T103', tipo: 'SO2', ubicacion: 'Sala C', estado: 'activo' },
];

test.describe('Dashboard Tecnico', () => {
  test.beforeEach(async ({ page }) => {
    await injectFakeAuth(page, 'tecnico');

    // pendientes
    await page.route(`${GW}/api/v1/incidencias?estado=pendiente**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_INCIDENCIAS_PENDIENTES) }),
    );
    // en_ejecucion and finalizado — empty
    await page.route(`${GW}/api/v1/incidencias**`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_LIST) }),
    );
    await page.route(`${IOT}/api/v1/iot/equipos`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPOS) }),
    );
    await page.route(`${GW}/api/v1/repuestos`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }),
    );
    await page.route(`${ML}/api/v1/predictions/**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [{ device_id: 'T103', failure_probability: 0.2, remaining_useful_life_days: 45, risk_level: 'media' }], total: 1 }),
      }),
    );

    await page.goto('/dashboard-tecnico');
  });

  test('renders tecnico dashboard heading', async ({ page }) => {
    await expect(page.getByText(/Mi Panel de Trabajo/i)).toBeVisible({ timeout: 10_000 });
  });

  test('shows KPI cards', async ({ page }) => {
    await expect(page.getByText(/Pendientes/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/En Ejecucion/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test('shows active incidencias section', async ({ page }) => {
    await expect(page.getByText(/Mis Incidencias Activas/i)).toBeVisible({ timeout: 10_000 });
  });

  test('shows equipos con incidencias section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Equipos con Incidencias/i })).toBeVisible({ timeout: 10_000 });
  });

  test('shows repuestos disponibles section', async ({ page }) => {
    await expect(page.getByText(/Repuestos Disponibles/i)).toBeVisible({ timeout: 10_000 });
  });

  test('header shows logout button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Salir/i })).toBeVisible({ timeout: 10_000 });
  });

  test('logout redirects to /login', async ({ page }) => {
    const logoutBtn = page.getByRole('button', { name: /Salir/i });
    await logoutBtn.waitFor({ timeout: 10_000 });
    await logoutBtn.click();
    await page.waitForURL('**/login', { timeout: 10_000 });
    expect(page.url()).toContain('/login');
  });
});
