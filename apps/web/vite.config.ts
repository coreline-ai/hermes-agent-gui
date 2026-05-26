import { defineConfig, type PluginOption } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import path from 'node:path';

const API_TARGET = process.env.VITE_API_BASE ?? 'http://127.0.0.1:8800';

export default defineConfig(async ({ mode }) => {
  const plugins: PluginOption[] = [
    TanStackRouterVite({
      routesDirectory: './src/routes',
      generatedRouteTree: './src/routeTree.gen.ts',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ];

  if (mode === 'singlefile') {
    // Phase 11: emit a single hermes-agent-gui.html (C's deploy mode).
    const { viteSingleFile } = await import('vite-plugin-singlefile');
    plugins.push(viteSingleFile());
  } else {
    // Phase 8: PWA (service worker + manifest) for all non-singlefile builds.
    const { VitePWA } = await import('vite-plugin-pwa');
    plugins.push(
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg', 'apple-touch-icon.svg', 'offline.html', 'sw-cleanup.js'],
        workbox: {
          // Never cache /api responses; credentials/tokens must not persist in Cache Storage.
          importScripts: ['sw-cleanup.js'],
          cleanupOutdatedCaches: true,
          // Navigation requests fall back to ``/offline.html`` when offline.
          navigateFallback: '/offline.html',
          navigateFallbackDenylist: [/^\/api\//],
          runtimeCaching: [
            {
              urlPattern: /\.(?:js|css|woff2?|png|svg)$/,
              handler: 'CacheFirst',
              options: { cacheName: 'assets', expiration: { maxEntries: 60 } },
            },
            {
              urlPattern: ({ request }) => request.mode === 'navigate',
              handler: 'NetworkFirst',
              options: { cacheName: 'pages', networkTimeoutSeconds: 3 },
            },
          ],
        },
        manifest: {
          name: 'Hermes Agent GUI',
          short_name: 'Hermes',
          description: 'One GUI for Hermes Agent.',
          theme_color: '#0ea5e9',
          background_color: '#0f172a',
          display: 'standalone',
          start_url: '/',
          icons: [
            { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml' },
            { src: '/apple-touch-icon.svg', sizes: '180x180', type: 'image/svg+xml', purpose: 'any maskable' },
          ],
        },
      }),
    );
  }

  return {
    plugins,
    resolve: {
      alias: { '@': path.resolve(__dirname, 'src') },
    },
    server: {
      port: 5173,
      proxy: { '/api': { target: API_TARGET, changeOrigin: true } },
    },
    build: {
      target: 'es2022',
      sourcemap: true,
    },
  };
});
