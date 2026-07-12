import { Page } from '@playwright/test';
import { GW } from './constants';

export const USERS = {
  admin: {
    email: 'admin@oefa.gob.pe',
    password: 'admin123',
    rol: 'administrador',
  },
  tecnico: {
    email: 'tecnico1@oefa.gob.pe',
    password: 'tecnico123',
    rol: 'tecnico',
  },
  coordinador: {
    email: 'coordinador1@oefa.gob.pe',
    password: 'coord123',
    rol: 'coordinador',
  },
};

const AUTH_ME = `${GW}/api/v1/auth/me`;

/**
 * Inject a fake JWT into localStorage and mock /auth/me so AuthProvider
 * doesn't redirect to /login when it validates the token on mount.
 * Call this BEFORE page.goto().
 */
export async function injectFakeAuth(
  page: Page,
  rol: 'administrador' | 'tecnico' | 'coordinador',
) {
  const fakeUser = {
    id: 1,
    email: 'admin@oefa.gob.pe',
    nombre: 'Test',
    apellido: 'User',
    rol,
  };

  // Mock /auth/me so the token validation in AuthProvider succeeds
  await page.route(AUTH_ME, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fakeUser),
    }),
  );

  // Inject token into localStorage before the page JS runs
  await page.addInitScript(
    ({ token, user }) => {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
    },
    { token: 'fake-jwt-token', user: fakeUser },
  );
}
