'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/lib/auth';

interface NavItem {
  label: string;
  href: string;
}

function NavLink({
  href,
  label,
  isActive,
}: {
  href: string;
  label: string;
  isActive: boolean;
}) {
  return (
    <Link
      href={href}
      className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        isActive
          ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50'
          : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50'
      }`}
    >
      {label}
    </Link>
  );
}

function Dropdown({ label, items }: { label: string; items: NavItem[] }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const isActive = items.some((item) => pathname.startsWith(item.href));

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className={`flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50'
            : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50'
        }`}
      >
        {label}
        <svg
          className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 z-50 mt-1 w-44 rounded-md border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
          {items.map((item) => {
            const subActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`block px-4 py-2 text-sm transition-colors ${
                  subActive
                    ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50'
                    : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

const ROL_LABEL: Record<string, string> = {
  administrador: 'Admin',
  tecnico: 'Tecnico',
  coordinador: 'Coordinador',
};

function getNavForRole(rol: string) {
  const mainItems: NavItem[] = [{ label: 'Inicio', href: '/' }];

  if (rol === 'administrador' || rol === 'coordinador') {
    mainItems.push({ label: 'Dashboard', href: '/dashboard' });
  } else if (rol === 'tecnico') {
    mainItems.push({ label: 'Dashboard', href: '/dashboard-tecnico' });
  }

  mainItems.push({ label: 'Equipos', href: '/equipos' });

  const opsItems: NavItem[] = [];
  if (rol === 'administrador' || rol === 'coordinador') {
    opsItems.push({ label: 'Incidencias', href: '/incidencias' });
    opsItems.push({ label: 'Problemas', href: '/problemas' });
    opsItems.push({ label: 'Calibraciones', href: '/calibraciones' });
    opsItems.push({ label: 'Reportes', href: '/reportes' });
  } else if (rol === 'tecnico') {
    opsItems.push({ label: 'Incidencias', href: '/incidencias' });
    opsItems.push({ label: 'Calibraciones', href: '/calibraciones' });
  }

  const afterItems: NavItem[] = [];
  if (rol !== 'tecnico') {
    afterItems.push({ label: 'Lecturas', href: '/lecturas' });
  }

  const adminItems: NavItem[] = [];
  if (rol === 'administrador') {
    adminItems.push({ label: 'Repuestos', href: '/repuestos' });
    adminItems.push({ label: 'Proveedores', href: '/proveedores' });
    adminItems.push({ label: 'Usuarios', href: '/usuarios' });
  } else if (rol === 'tecnico') {
    adminItems.push({ label: 'Repuestos', href: '/repuestos' });
  }

  return { mainItems, opsItems, afterItems, adminItems };
}

export default function Header() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  const rol = user?.rol ?? 'coordinador';
  const { mainItems, opsItems, afterItems, adminItems } = getNavForRole(rol);

  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
            Air Monitoring
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {mainItems.map((item) => {
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href);
            return (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                isActive={isActive}
              />
            );
          })}

          {opsItems.length > 0 && (
            <Dropdown label="Operaciones" items={opsItems} />
          )}

          {afterItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                isActive={isActive}
              />
            );
          })}

          {adminItems.length > 1 ? (
            <Dropdown label="Administracion" items={adminItems} />
          ) : adminItems.length === 1 ? (
            <NavLink
              href={adminItems[0].href}
              label={adminItems[0].label}
              isActive={pathname.startsWith(adminItems[0].href)}
            />
          ) : null}
        </nav>

        {isAuthenticated && user && (
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {user.nombre} {user.apellido}
              </div>
              <div className="text-xs text-zinc-500">
                {ROL_LABEL[user.rol] ?? user.rol}
              </div>
            </div>
            <button
              onClick={logout}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Salir
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
