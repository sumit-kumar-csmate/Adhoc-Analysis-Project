const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        backgroundColor: '#1a1a2e',
        titleBarStyle: 'default',
        icon: path.join(__dirname, '../assets/icon.png')
    });

    // Maximize the window on startup
    mainWindow.maximize();

    // Load the frontend
    mainWindow.loadURL('http://127.0.0.1:5000');

    // Open DevTools in development
    if (process.env.NODE_ENV === 'development') {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Start Flask backend
function startBackend() {
    // Check if backend is already running (e.g. in development)
    const http = require('http');
    const req = http.get('http://127.0.0.1:5000/api/materials', (res) => {
        console.log('Backend already running on port 5000. Skipping spawn.');
        // Backend is reachable, no need to spawn
    });

    req.on('error', (e) => {
        // Backend not running, spawn it
        console.log('Backend not reachable, spawning process...');
        spawnBackendProcess();
    });
}

function spawnBackendProcess() {
    const isWindows = process.platform === 'win32';
    const pythonCmd = isWindows ? 'python' : 'python3';
    const venvPython = isWindows
        ? path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
        : path.join(__dirname, '..', 'venv', 'bin', 'python');

    const backendPath = path.join(__dirname, '..', 'backend', 'flask_app.py');

    // Try venv python first, fallback to system python
    const pythonPath = require('fs').existsSync(venvPython) ? venvPython : pythonCmd;

    backendProcess = spawn(pythonPath, [backendPath], {
        cwd: path.join(__dirname, '..'),
        stdio: 'ignore',
        windowsHide: true
    });

    backendProcess.on('error', (err) => {
        console.error('Failed to start backend:', err);
    });

    backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
    });
}

// Handle file selection
ipcMain.handle('select-file', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            { name: 'Data Files', extensions: ['xlsx', 'xls', 'csv'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
        return result.filePaths[0];
    }
    return null;
});

app.on('ready', () => {
    startBackend();

    // Wait for backend to start
    setTimeout(() => {
        createWindow();
    }, 2000);
});

app.on('window-all-closed', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

app.on('before-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
