import { test, expect, type Page } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { IOT } from './helpers/constants';

// C8: onboarding automático — equipos en cuarentena (no_confirmado) aparecen en el
// panel "Equipos por confirmar" en /equipos, y el coordinador/admin los confirma.

const MOCK_EQUIPOS = [
  {
    device_id: 'T101',
    nombre: 'Analizador SO2',
    tipo: 'SO2',
    ubicacion: 'Sala A',
    estado: 'activo',
  },
];

const MOCK_PENDIENTES = [
  {
    device_id: 'T500',
    estado: 'no_confirmado',
    criticidad: 'media',
    fecha_registro: new Date().toISOString(),
  },
];

async function setupMocks(page: Page, pendientes = MOCK_PENDIENTES) {
  await page.route(`${IOT}/api/v1/iot/equipos`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_EQUIPOS),
    }),
  );
  await page.route(`${IOT}/api/v1/iot/equipos/pendientes`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(pendientes),
    }),
  );
  await page.route(`${IOT}/api/v1/iot/equipos/T500/confirmar`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        device_id: 'T500',
        estado: 'activo',
        criticidad: 'alta',
        fecha_registro: new Date().toISOString(),
      }),
    }),
  );
}

test.describe('Equipos onboarding (C8)', () => {
  test('coordinador ve el panel de equipos por confirmar', async ({ page }) => {
    await injectFakeAuth(page, 'coordinador');
    await setupMocks(page);
    await page.goto('/equipos', { waitUntil: 'domcontentloaded' });

    await expect(page.getByText(/Equipos por confirmar/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText('T500')).toBeVisible();
    await expect(
      page.getByRole('button', { name: /Confirmar/i }),
    ).toBeVisible();
  });

  test('confirmar un equipo lo quita del panel', async ({ page }) => {
    await injectFakeAuth(page, 'coordinador');
    await setupMocks(page);
    await page.goto('/equipos', { waitUntil: 'domcontentloaded' });

    await page.getByRole('button', { name: /Confirmar/i }).click();
    // tras confirmar, la fila T500 desaparece del panel
    await expect(page.getByText('T500')).toHaveCount(0, { timeout: 10_000 });
  });

  test('sin equipos pendientes el panel no aparece', async ({ page }) => {
    await injectFakeAuth(page, 'coordinador');
    await setupMocks(page, []);
    await page.goto('/equipos', { waitUntil: 'domcontentloaded' });

    await expect(page.getByText(/Equipos$/i).first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/Equipos por confirmar/i)).toHaveCount(0);
  });
});
