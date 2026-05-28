import { defineConfig, type PluginOption } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import path from 'node:path';

const API_TARGET = process.env.VITE_API_BASE ?? 'http://127.0.0.1:8800';
const PUBLISH_SOURCEMAPS = process.env.HERMES_GUI_PUBLISH_SOURCEMAPS === '1';

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
          sourcemap: PUBLISH_SOURCEMAPS,
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
      proxy: { '/api': { target: API_TARGET, changeOrigin: true, xfwd: true } },
    },
    build: {
      target: 'es2022',
      sourcemap: PUBLISH_SOURCEMAPS,
      // The only expected large chunk is the lazy-loaded Three.js core used by
      // the opt-in 3D office route. Keep the warning budget below 1MB so new
      // accidental main-route bloat still surfaces.
      chunkSizeWarningLimit: 800,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined;
            if (/[\\/]node_modules[\\/]three[\\/](build|src)[\\/]/.test(id)) return 'vendor-three-core';
            if (/[\\/]node_modules[\\/]three[\\/]examples[\\/]/.test(id)) return 'vendor-three-extras';
            if (/[\\/]node_modules[\\/](@react-three|@dimforge|ecctrl)[\\/]/.test(id)) return 'vendor-3d';
            if (/[\\/]node_modules[\\/](recharts|d3-[^\\/]+|victory|@visx)[\\/]/.test(id)) return 'vendor-charts';
            if (/[\\/]node_modules[\\/](@tanstack)[\\/]/.test(id)) return 'vendor-tanstack';
            if (/[\\/]node_modules[\\/](react|react-dom|scheduler|use-sync-external-store)[\\/]/.test(id)) return 'vendor-react';
            return undefined;
          },
        },
      },
    },
  };
});
