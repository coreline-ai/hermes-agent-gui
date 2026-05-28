/* eslint-disable */
// hermes-agent-gui — Electron main process (Phase 12, unsigned dev build).
// Spawns the Python backend as a child process, then opens a BrowserWindow
// pointing at it. Mirrors A's electron/main.cjs structure but trimmed.

const { app, BrowserWindow, shell, ipcMain } = require('electron');
const path = require('node:path');
const { spawn } = require('node:child_process');
const http = require('node:http');
let autoUpdater = null;
try {
  ({ autoUpdater } = require('electron-updater'));
} catch {
  autoUpdater = null;
}

const PORT = Number(process.env.HERMES_GUI_PORT || 8800);
const HOST = process.env.HERMES_GUI_HOST || '127.0.0.1';

function devPath(...segments) {
  return path.join(__dirname, '..', ...segments);
}

function resourcePath(...segments) {
  return app.isPackaged ? path.join(process.resourcesPath, ...segments) : devPath(...segments);
}

const SERVER_ENTRY = app.isPackaged
  ? resourcePath('server', 'server.py')
  : devPath('apps', 'server', 'server.py');
const WEB_DIST = app.isPackaged
  ? resourcePath('web')
  : devPath('apps', 'web', 'dist');

let backendProcess = null;
let mainWindow = null;

function spawnBackend() {
  const args = [SERVER_ENTRY, '--host', HOST, '--port', String(PORT)];
  backendProcess = spawn('python3', args, {
    stdio: ['ignore', 'inherit', 'inherit'],
    env: {
      ...process.env,
      HERMES_GUI_PASSWORD: process.env.HERMES_GUI_PASSWORD || '',
      HERMES_GUI_WEB_DIST: process.env.HERMES_GUI_WEB_DIST || WEB_DIST,
    },
  });
  backendProcess.on('exit', (code) => {
    console.log(`[hermes-gui] backend exit code=${code}`);
    backendProcess = null;
    if (mainWindow) mainWindow.close();
  });
}

async function waitForHealth(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await new Promise((res, rej) => {
        const req = http.get(`http://${HOST}:${PORT}/api/health`, (r) => {
          r.statusCode === 200 ? res(undefined) : rej(new Error(`status ${r.statusCode}`));
          r.resume();
        });
        req.on('error', rej);
        req.setTimeout(2000, () => req.destroy(new Error('timeout')));
      });
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  return false;
}

function wireAutoUpdater() {
  if (!autoUpdater || !mainWindow) return;
  autoUpdater.on('update-available', (info) => {
    mainWindow.webContents.send('update-available', { version: info.version || 'new' });
  });
  ipcMain.handle('download-update', async () => autoUpdater.downloadUpdate());
  autoUpdater.checkForUpdatesAndNotify().catch((err) => {
    console.log(`[hermes-gui] updater skipped: ${err.message}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: 'Hermes Agent GUI',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.loadURL(`http://${HOST}:${PORT}`);
  wireAutoUpdater();
}

app.whenReady().then(async () => {
  spawnBackend();
  const ok = await waitForHealth();
  if (!ok) {
    console.error('[hermes-gui] backend never became healthy — aborting');
    app.quit();
    return;
  }
  createWindow();
});

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill();
});
