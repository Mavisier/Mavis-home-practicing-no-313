import js from '@eslint/js';
import ts from 'typescript-eslint';

export default ts.config(
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  { files: ['src/**/*.{ts,tsx}'], languageOptions: { globals: {
    fetch: 'readonly', AbortSignal: 'readonly', RequestInit: 'readonly',
    document: 'readonly', window: 'readonly', console: 'readonly',
  } } },
  { files: ['vite.config.ts'], languageOptions: { globals: { process: 'readonly' } } },
);
