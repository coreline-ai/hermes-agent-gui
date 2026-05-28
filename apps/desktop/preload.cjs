/* eslint-disable */
// hermes-agent-gui — Electron preload (Phase 12).
// Minimal — context-isolated. Exposes nothing yet; future phases can bridge
// auto-update / native menus through contextBridge here.
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('hermesElectron', {
  version: process.env.npm_package_version || 'dev',
  platform: process.platform,
  onUpdateAvailable: (cb) => ipcRenderer.on('update-available', (_event, info) => cb(info)),
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
});
