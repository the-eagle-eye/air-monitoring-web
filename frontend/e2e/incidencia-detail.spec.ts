import { test, expect, type Page } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { GW, EMPTY_LIST } from './helpers/constants';

const MOCK_INCIDENCIA = {
  id: 1,
  device_id: 'T102',
  tipo: 'correctiva',
  descripcion: 'Falla detectada por RUL critico',
  estado: 'pendiente',
  prioridad: 'alta',
  responsable_id: null,
  mantenimiento_correctivo: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_USUARIOS = [
  { id: 1, email: 'tecnico1@oefa.gob.pe', nombre: 'Juan', apellido: 'Perez', rol: 'tecnico', estado: 'activo' },
];

const MOCK_REPUESTOS = [
  { id: 1, nombre: 'Filtro UV', categoria: 'Filtros', estado: 'activo' },
  { id: 2, nombre: 'Bomba de muestra', categoria: 'Bombas', estado: 'activo' },
];

// Registers all API mocks. Must be called before page.goto().
// Playwright route order: most-recently registered takes precedence, so the
// catch-all MUST be registered FIRST and specific routes LAST.
async function setupMocks(page: Page, incidencia = MOCK_INCIDENCIA) {
  // Catch-all registered first (lowest priority)
  await page.route(`${GW}/api/v1/incidencias**`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(EMPTY_LIST) }),
  );
  await page.route(`${GW}/api/v1/usuarios`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_USUARIOS) }),
  );
  await page.route(`${GW}/api/v1/repuestos`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_REPUESTOS) }),
  );
  await page.route(`${GW}/api/v1/incidencias/1/mantenimiento`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) }),
  );
  // Specific incidencia route registered last (highest priority)
  await page.route(`${GW}/api/v1/incidencias/1`, (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(incidencia) });
    } else {
      let parsed = {};
      try { parsed = JSON.parse(route.request().postData() ?? '{}'); } catch { /* ignore */ }
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...incidencia, ...parsed }) });
    }
  });
}

// Warm up the dynamic route, then navigate to the target path.
// Next.js dev server compiles [id] routes lazily; hitting /incidencias first
// triggers compilation so the subsequent /incidencias/1 request succeeds.
async function gotoIncidencia(page: Page, path = '/incidencias/1') {
  await page.goto('/incidencias', { waitUntil: 'domcontentloaded' });
  await page.goto(path, { waitUntil: 'domcontentloaded' });
}

test.describe('Incidencia detail page', () => {
  test('renders incidencia metadata in read-only mode', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    await expect(page.getByText('Incidencia #1')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('T102').first()).toBeVisible();
    await expect(page.getByText(/Solo lectura/i)).toBeVisible();
    await expect(page.getByText(/Alta/i).first()).toBeVisible();
  });

  test('Editar button switches to edit mode', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    const editBtn = page.getByRole('link', { name: /Editar/i });
    await editBtn.waitFor({ timeout: 15_000 });
    await editBtn.click();

    await page.waitForURL('**/incidencias/1?mode=edit');
    await expect(page.getByText(/Editando/i)).toBeVisible();
    await expect(page.locator('select').first()).toBeVisible();
  });

  test('edit mode shows estado dropdown with all options', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page, '/incidencias/1?mode=edit');

    const estadoSelect = page.locator('select').first();
    await estadoSelect.waitFor({ timeout: 15_000 });

    await expect(estadoSelect.locator('option[value="pendiente"]')).toBeAttached();
    await expect(estadoSelect.locator('option[value="en_ejecucion"]')).toBeAttached();
    await expect(estadoSelect.locator('option[value="finalizado"]')).toBeAttached();
    await expect(estadoSelect.locator('option[value="cancelado"]')).toBeAttached();
  });

  test('edit mode shows responsable dropdown with usuarios', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page, '/incidencias/1?mode=edit');

    await expect(page.locator('select')).toHaveCount(2, { timeout: 15_000 });
    const responsableSelect = page.locator('select').nth(1);
    await expect(responsableSelect.locator('option', { hasText: 'Juan Perez' })).toBeAttached();
  });

  test('saving without responsable shows validation error', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page, '/incidencias/1?mode=edit');

    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 15_000 });

    // Fill mantenimiento fields (required) but leave responsable empty
    await page.locator('textarea').nth(0).fill('Sensor degradado');
    await page.locator('textarea').nth(1).fill('Reemplazo UV');
    await page.locator('textarea').nth(2).fill('Equipo operativo');

    await page.getByRole('button', { name: /Guardar/i }).click();
    await expect(page.getByText(/Responsable es obligatorio/i)).toBeVisible({ timeout: 5_000 });
  });

  test('Ver Equipo link points to correct device', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    const link = page.getByRole('link', { name: /Ver Equipo/i });
    await link.waitFor({ timeout: 15_000 });
    await expect(link).toHaveAttribute('href', '/equipos/T102');
  });

  test('finalizado incidencia hides Editar button', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page, { ...MOCK_INCIDENCIA, estado: 'finalizado' });
    await gotoIncidencia(page);

    await expect(page.getByText('Incidencia #1')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('link', { name: /Editar/i })).not.toBeVisible();
  });
});
