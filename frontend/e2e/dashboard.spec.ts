import { test, expect } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { IOT, GW, EMPTY_LIST } from './helpers/constants';

const MOCK_EQUIPOS = [
  {
    device_id: 'T101',
    nombre: 'Analizador SO2 T101',
    tipo: 'SO2',
    ubicacion: 'Sala A',
    estado: 'activo',
  },
  {
    device_id: 'T102',
    nombre: 'Analizador H2S T102',
    tipo: 'H2S',
    ubicacion: 'Sala B',
    estado: 'activo',
  },
];

// Estado de salud del ensemble (modelo vigente). T101 sano, T102 en riesgo.
const HEALTH_STATE: Record<string, object> = {
  T101: {
    device_id: 'T101',
    health_state: 'SANO',
    last_recon_error: 0.02,
    theta: 0.05,
    hours_since_prev: 120,
    transmission_state: 'OK',
    transmission_severity: null,
    last_reading_ts: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  T102: {
    device_id: 'T102',
    health_state: 'EN_RIESGO',
    last_recon_error: 0.12,
    theta: 0.05,
    hours_since_prev: 4,
    transmission_state: 'OK',
    transmission_severity: null,
    last_reading_ts: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
};

const HEALTH_READINGS = {
  device_id: 'T101',
  points: [
    {
      timestamp: new Date().toISOString(),
      recon_error: 0.02,
      theta: 0.05,
      health_state: 'SANO',
      and_alert: false,
    },
  ],
};

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await injectFakeAuth(page, 'administrador');

    await page.route(`${IOT}/api/v1/iot/equipos`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_EQUIPOS),
      }),
    );
    // Monitor de salud (ensemble) — vía gateway. state por equipo y readings.
    await page.route(`${GW}/api/v1/health-monitor/*/state`, (route) => {
      const m = route
        .request()
        .url()
        .match(/health-monitor\/([^/]+)\/state/);
      const id = m ? m[1] : 'T101';
      const state = HEALTH_STATE[id];
      if (!state)
        return route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: '{}',
        });
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state),
      });
    });
    await page.route(`${GW}/api/v1/health-monitor/*/readings**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(HEALTH_READINGS),
      }),
    );
    await page.route(`${GW}/api/v1/incidencias**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_LIST),
      }),
    );
    await page.route(`${GW}/api/v1/calibraciones**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_LIST),
      }),
    );
    // ITIL: reincidentes (sugerencia de problema) + resumen de problemas
    await page.route(`${GW}/api/v1/problemas/reincidentes**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ dias: 90, min_correctivas: 3, items: [] }),
      }),
    );
    await page.route(`${GW}/api/v1/problemas/resumen`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ por_estado: {}, abiertos: 0, total: 0 }),
      }),
    );
    await page.route(`${IOT}/api/v1/iot/readings/**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_LIST),
      }),
    );

    await page.goto('/dashboard');
  });

  test('renders ensemble KPI cards', async ({ page }) => {
    await expect(page.getByText(/Equipos monitoreados/i).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/Equipos con anomal/i).first()).toBeVisible();
    await expect(page.getByText(/Incidencias abiertas/i).first()).toBeVisible();
    await expect(page.getByText(/Sin transmisi/i).first()).toBeVisible();
  });

  test('renders health semaforo (Salud Predictiva)', async ({ page }) => {
    await expect(page.getByText(/Salud Predictiva/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('renders equipment grid with device cards', async ({ page }) => {
    await expect(page.getByText('T101').first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText('T102').first()).toBeVisible();
  });

  test('equipment card links to detail page', async ({ page }) => {
    await page.getByText('T101').first().waitFor({ timeout: 10_000 });
    await expect(
      page.locator('a[href*="/equipos/T101"]').first(),
    ).toBeVisible();
  });

  test('distribución de salud section is visible', async ({ page }) => {
    await expect(page.getByText(/Distribuci.n de Salud/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('tendencia de anomalías section is visible', async ({ page }) => {
    await expect(page.getByText(/Tendencia de Anomal/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('incidencias summary section is visible', async ({ page }) => {
    await expect(page.getByText(/Incidencias/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('proximas calibraciones section is visible', async ({ page }) => {
    await expect(page.getByText(/Calibraciones/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('nav does NOT show legacy Predicciones/Alertas items', async ({
    page,
  }) => {
    await expect(page.getByText(/Equipos monitoreados/i).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole('link', { name: 'Predicciones' })).toHaveCount(
      0,
    );
    await expect(page.getByRole('link', { name: 'Alertas' })).toHaveCount(0);
  });

  test('header shows logged-in user and logout button', async ({ page }) => {
    await expect(page.getByText(/Test User|Admin/i).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole('button', { name: /Salir/i })).toBeVisible();
  });

  test('logout redirects to /login', async ({ page }) => {
    const logoutBtn = page.getByRole('button', { name: /Salir/i });
    await logoutBtn.waitFor({ timeout: 10_000 });
    await logoutBtn.click();
    await page.waitForURL('**/login', { timeout: 10_000 });
    expect(page.url()).toContain('/login');
  });

  // Caso 1: un equipo con salud SANO pero incidencia correctiva abierta debe
  // seguir visible en "Equipos que requieren atención" como "En seguimiento".
  test('equipo SANO con incidencia abierta aparece como En seguimiento', async ({
    page,
  }) => {
    // T101 está SANO en HEALTH_STATE; le damos una correctiva abierta.
    const openInc = {
      items: [
        {
          id: 42,
          device_id: 'T101',
          tipo: 'correctiva',
          estado: 'en_ejecucion',
          prioridad: 'alta',
          origen: 'monitor_salud',
          responsable_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
    };
    // re-registrar la ruta de incidencias (la última registrada tiene prioridad)
    await page.route(`${GW}/api/v1/incidencias**`, (route) => {
      const url = route.request().url();
      // el dashboard pide pendiente y en_ejecucion por separado
      if (url.includes('estado=en_ejecucion')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(openInc),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(EMPTY_LIST),
      });
    });
    await page.goto('/dashboard');

    const seccion = page
      .locator('div', { hasText: /Equipos que requieren atenci/i })
      .last();
    await expect(seccion.getByText('En seguimiento').first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      seccion.getByText(/incidencia abierta/i).first(),
    ).toBeVisible();
  });

  // ITIL Problemas visible/proactivo: un equipo reincidente sugiere abrir un
  // problema, y "Crear problema" lo crea + vincula las incidencias.
  test('equipo reincidente sugiere crear problema y lo crea al pulsar', async ({
    page,
  }) => {
    await page.route(`${GW}/api/v1/problemas/reincidentes**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          dias: 90,
          min_correctivas: 3,
          items: [
            {
              device_id: 'T102',
              correctivas: 4,
              desde: new Date().toISOString(),
              incidencia_ids: [10, 11, 12, 13],
            },
          ],
        }),
      }),
    );
    let problemaCreado = false;
    await page.route(`${GW}/api/v1/problemas`, (route) => {
      if (route.request().method() === 'POST') {
        problemaCreado = true;
        return route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 7,
            device_id: 'T102',
            titulo: 'x',
            estado: 'abierto',
            created_at: new Date().toISOString(),
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });
    // vincular incidencias al problema (POST /incidencias/{id}/problema)
    await page.route(`${GW}/api/v1/incidencias/*/problema`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 10, problema_id: 7 }),
      }),
    );
    await page.goto('/dashboard');

    // el badge "4 correctivas / 90d" es único del widget de reincidentes
    await expect(page.getByText(/4 correctivas \/ 90d/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByRole('button', { name: /Crear problema/i }),
    ).toBeVisible();

    await page.getByRole('button', { name: /Crear problema/i }).click();
    await expect(page.getByText(/Problema #7 creado/i)).toBeVisible({
      timeout: 10_000,
    });
    expect(problemaCreado).toBe(true);
  });
});
