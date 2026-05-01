import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ mode }) => {
  const localEnv = loadEnv(mode, process.cwd(), 'VITE_');

  // Ensure local .env values win over injected process env (e.g. Infisical).
  Object.entries(localEnv).forEach(([key, value]) => {
    process.env[key] = value;
  });

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    esbuild: {
      drop: [],
    },
  };
});
