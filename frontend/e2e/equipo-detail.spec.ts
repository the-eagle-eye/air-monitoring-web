import { test, expect } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { IOT, GW } from './helpers/constants';

const DEVICE_ID = 'T101';

const MOCK_EQUIPO = {
  device_id: DEVICE_ID,
  nombre: 'Analizador SO2 T101',
  tipo: 'SO2',
  ubicacion: 'Sala A',
  estado: 'activo',
  serie: 'SN-001',
  marca: 'Thermo Fisher',
  modelo: 'Model 43i',
  parametro_medicion: 'SO2',
  rango_medicion: '0-500 ppb',
  fecha_ingreso: '2023-01-15',
  fecha_registro: new Date().toISOString(),
};

// Serie de salud del ensemble (modelo vigente) — reemplaza predicciones RF.
const MOCK_HEALTH_READINGS = {
  device_id: DEVICE_ID,
  points: [
    {
      timestamp: new Date(Date.now() - 3600_000).toISOString(),
      recon_error: 0.03,
      theta: 0.05,
      health_state: 'SANO',
      and_alert: false,
      if_anomaly: false,
      severity: null,
    },
    {
      timestamp: new Date().toISOString(),
      recon_error: 0.02,
      theta: 0.05,
      health_state: 'SANO',
      and_alert: false,
      if_anomaly: false,
      severity: null,
    },
  ],
};

const MOCK_LECTURAS = {
  items: [
    {
      id: 1,
      device_id: 1,
      equipo_device_id: DEVICE_ID,
      so2_ppb: 12.5,
      h2s_ppb: 0.3,
      reaction_temp: 45.2,
      box_temp: 30.1,
      sample_flow: 0.5,
      uv_lamp_intensity: 98.0,
      timestamp_lectura: new Date().toISOString(),
      procesado: true,
      created_at: new Date().toISOString(),
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
};

const EMPTY = { items: [], total: 0 };

test.describe('Equipo detail page', () => {
  test.beforeEach(async ({ page }) => {
    await injectFakeAuth(page, 'administrador');

    await page.route(`${IOT}/api/v1/iot/equipos/${DEVICE_ID}`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_EQUIPO),
      }),
    );
    await page.route(`${IOT}/api/v1/iot/readings/${DEVICE_ID}**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LECTURAS),
      }),
    );
    // Salud del ensemble (readings recon_error + θ) vía gateway.
    await page.route(
      `${GW}/api/v1/health-monitor/${DEVICE_ID}/readings**`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_HEALTH_READINGS),
        }),
    );
    await page.route(
      `${GW}/api/v1/health-monitor/${DEVICE_ID}/state`,
      (route) =>
        route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: '{}',
        }),
    );
    await page.route(`${GW}/api/v1/incidencias**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY),
      }),
    );
    await page.route(`${GW}/api/v1/calibraciones**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY),
      }),
    );

    await page.goto(`/equipos/${DEVICE_ID}`);
  });

  test('shows equipo name and device ID', async ({ page }) => {
    await expect(page.getByText(DEVICE_ID).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText('Analizador SO2 T101').first()).toBeVisible();
  });

  test('tabs are rendered (Resumen, Salud, Lecturas, Historial)', async ({
    page,
  }) => {
    await expect(page.getByRole('button', { name: 'Resumen' })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole('button', { name: 'Salud' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Lecturas' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Historial' })).toBeVisible();
  });

  test('legacy Alertas tab is NOT rendered', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Resumen' })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole('button', { name: 'Alertas' })).toHaveCount(0);
  });

  test('Resumen tab shows health (salud predictiva) info', async ({ page }) => {
    await expect(
      page.getByText(/Salud|reconstrucci.n|Estado/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('clicking Salud tab shows recon error chart', async ({ page }) => {
    await page.getByRole('button', { name: 'Salud' }).click();
    await expect(
      page.getByText(/reconstrucci.n|umbral|θ/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  // M3: panel de desglose de los 2 detectores en el tab Salud
  test('Salud tab shows detector breakdown panel (AE / IF / AND)', async ({
    page,
  }) => {
    await page.getByRole('button', { name: 'Salud' }).click();
    await expect(page.getByText(/desglose de detectores/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/Autoencoder/i).first()).toBeVisible();
    await expect(page.getByText(/Isolation Forest/i).first()).toBeVisible();
    await expect(page.getByText(/Compuerta AND/i).first()).toBeVisible();
  });

  test('clicking Lecturas tab shows sensor data', async ({ page }) => {
    await page.getByRole('button', { name: 'Lecturas' }).click();
    await expect(page.getByText(/SO2|12\.5/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('clicking Historial tab renders without error', async ({ page }) => {
    await page.getByRole('button', { name: 'Historial' }).click();
    await expect(
      page.getByText(/Historial|mantenimiento|correctivo|calibraci/i).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('back link navigates to /equipos list', async ({ page }) => {
    await expect(page.locator('a[href="/equipos"]').first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('equipo metadata fields are displayed', async ({ page }) => {
    await expect(page.getByText('Thermo Fisher').first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText('Model 43i').first()).toBeVisible();
  });
});
