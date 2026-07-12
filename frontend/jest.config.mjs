import nextJest from 'next/jest.js';

// next/jest wires up SWC (same transformer as the real build — no Babel),
// loads next.config + .env files, and handles CSS/asset mocking for us.
const createJestConfig = nextJest({ dir: './' });

/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    // Mirror the tsconfig "@/*" path alias.
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  // Only unit/integration specs — Playwright E2E lives under e2e/ and runs separately.
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/e2e/'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/types/**',
    '!src/app/**/layout.tsx',
  ],
};

export default createJestConfig(config);
