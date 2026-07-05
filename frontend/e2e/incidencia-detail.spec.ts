import { test, expect, type Page } from '@playwright/test';
import { injectFakeAuth } from './helpers/auth';
import { GW, EMPTY_LIST } from './helpers/constants';

const MOCK_INCIDENCIA: Record<string, unknown> = {
  id: 1,
  device_id: 'T102',
  tipo: 'correctiva',
  descripcion: 'Monitor de salud: anomalia CRITICO confirmada (ensemble AE+IF)',
  estado: 'pendiente',
  prioridad: 'alta',
  origen: 'monitor_salud',
  responsable_id: null,
  mantenimiento_correctivo: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_USUARIOS = [
  { id: 1, email: 'tecnico1@oefa.gob.pe', nombre: 'Juan', apellido: 'Perez', rol: 'tecnico', estado: 'activo' },
  { id: 2, email: 'tecnico2@oefa.gob.pe', nombre: 'Ana', apellido: 'Lopez', rol: 'tecnico', estado: 'activo' },
  { id: 3, email: 'exttecnico@oefa.gob.pe', nombre: 'Baja', apellido: 'Retirado', rol: 'tecnico', estado: 'inactivo' },
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
  await page.route(`${GW}/api/v1/problemas**`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) }),
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

test.describe('Incidencia detail page (flujo ITIL por rol)', () => {
  test('renders incidencia metadata + estado badge', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    await expect(page.getByText('Incidencia #1')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('T102').first()).toBeVisible();
    await expect(page.getByText(/Alta/i).first()).toBeVisible();
  });

  // Coordinador: incidencia pendiente -> puede ASIGNAR técnico (no exige mantenimiento)
  test('coordinador can assign technician on pendiente (no mantenimiento required)', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    // botón Asignar visible; selector de técnico presente
    await expect(page.getByRole('button', { name: /^Asignar$/i })).toBeVisible({ timeout: 15_000 });
    const tecSelect = page.locator('select').first();
    await expect(tecSelect.locator('option', { hasText: 'Juan Perez' })).toBeAttached();
    // NO se le pide llenar mantenimiento para asignar (no hay botón "Guardar mantenimiento")
    await expect(page.getByRole('button', { name: /Guardar mantenimiento/i })).toHaveCount(0);
  });

  // Coordinador: incidencia YA asignada (en_ejecucion) -> puede RE-ASIGNAR;
  // la lista de responsables muestra solo técnicos ACTIVOS (excluye inactivos).
  test('coordinador can re-assign on en_ejecucion; only active tecnicos listed', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page, { ...MOCK_INCIDENCIA, estado: 'en_ejecucion', responsable_id: 1 });
    await gotoIncidencia(page);

    // botón "Re-asignar" visible (no "Asignar")
    await expect(page.getByRole('button', { name: /Re-asignar/i })).toBeVisible({ timeout: 15_000 });
    const tecSelect = page.locator('select').first();
    // técnicos activos presentes
    await expect(tecSelect.locator('option', { hasText: 'Juan Perez' })).toBeAttached();
    await expect(tecSelect.locator('option', { hasText: 'Ana Lopez' })).toBeAttached();
    // técnico inactivo NO aparece
    await expect(tecSelect.locator('option', { hasText: 'Baja Retirado' })).toHaveCount(0);
  });

  // Coordinador: incidencia resuelta -> puede VERIFICAR Y CERRAR
  test('coordinador sees Verificar y cerrar on resuelto', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page, { ...MOCK_INCIDENCIA, estado: 'resuelto', responsable_id: 1,
      mantenimiento_correctivo: { id: 1, diagnostico: 'd', acciones_realizadas: 'a', conclusion: 'c' } });
    await gotoIncidencia(page);

    await expect(page.getByRole('button', { name: /Verificar y cerrar/i })).toBeVisible({ timeout: 15_000 });
  });

  // Técnico: incidencia en_ejecucion asignada -> ve el formulario de mantenimiento
  test('tecnico sees mantenimiento form on en_ejecucion', async ({ page }) => {
    await injectFakeAuth(page, 'tecnico');
    await setupMocks(page, { ...MOCK_INCIDENCIA, estado: 'en_ejecucion', responsable_id: 1 });
    await gotoIncidencia(page);

    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: /Guardar mantenimiento/i })).toBeVisible();
    // el técnico NO ve acciones de coordinador
    await expect(page.getByRole('button', { name: /Verificar y cerrar/i })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /^Asignar$/i })).toHaveCount(0);
  });

  test('Ver Equipo link points to correct device', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page);
    await gotoIncidencia(page);

    const link = page.getByRole('link', { name: /Ver Equipo/i });
    await link.waitFor({ timeout: 15_000 });
    await expect(link).toHaveAttribute('href', '/equipos/T102');
  });

  // Incidencia cerrada: sin botones de acción
  test('finalizado incidencia has no action buttons', async ({ page }) => {
    await injectFakeAuth(page, 'administrador');
    await setupMocks(page, { ...MOCK_INCIDENCIA, estado: 'finalizado' });
    await gotoIncidencia(page);

    await expect(page.getByText('Incidencia #1')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: /Asignar|Verificar y cerrar/i })).toHaveCount(0);
  });
});
