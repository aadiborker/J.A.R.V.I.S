const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn, spawnSync } = require("child_process");
const WebSocket = require("ws");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const WS_URL = process.env.JARVIS_WS_URL || "ws://127.0.0.1:8765";
const LOG_DIR = path.join(PROJECT_ROOT, "tmp");
const LOG_FILE = path.join(LOG_DIR, "jarvis-backend.log");

// Prevent multiple desktop icons from launching multiple Jarvis cores (double speech).
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}

let mainWindow = null;
let pythonProc = null;
let tray = null;
let isQuitting = false;
let bridgeSocket = null;

function trayIcon() {
  const iconPath = path.join(__dirname, "assets", "tray.png");
  const img = nativeImage.createFromPath(iconPath);
  return img.isEmpty() ? nativeImage.createEmpty() : img;
}

function showWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }
  mainWindow.show();
  mainWindow.focus();
}

function createTray() {
  tray = new Tray(trayIcon());
  tray.setToolTip("J.A.R.V.I.S");
  const menu = Menu.buildFromTemplate([
    { label: "Show HUD", click: () => showWindow() },
    { type: "separator" },
    {
      label: "Quit J.A.R.V.I.S",
      click: () => {
        isQuitting = true;
        stopPython();
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(menu);
  tray.on("double-click", () => showWindow());
}

function connectBridgeSocket() {
  if (bridgeSocket && (bridgeSocket.readyState === WebSocket.OPEN || bridgeSocket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  try {
    bridgeSocket = new WebSocket(WS_URL);
    bridgeSocket.on("error", () => {
      /* backend may still be booting */
    });
    bridgeSocket.on("close", () => {
      bridgeSocket = null;
      if (!isQuitting) {
        setTimeout(connectBridgeSocket, 1500);
      }
    });
  } catch (_) {
    setTimeout(connectBridgeSocket, 1500);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 600,
    minWidth: 720,
    minHeight: 460,
    frame: false,
    transparent: false,
    backgroundColor: "#05080f",
    alwaysOnTop: false,
    title: "J.A.R.V.I.S",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // X means quit (stop mic/TTS). Use Minimize or tray "Show HUD" to keep running.
  mainWindow.on("close", () => {
    isQuitting = true;
    stopPython();
  });
}

function resolvePython() {
  if (process.env.JARVIS_PYTHON && fs.existsSync(process.env.JARVIS_PYTHON)) {
    return process.env.JARVIS_PYTHON;
  }

  const candidates = [
    path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python312", "python.exe"),
    path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python311", "python.exe"),
    path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python313", "python.exe"),
  ];
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) return candidate;
  }

  // Prefer `py -3` resolution on Windows (avoids Windows Store stub).
  try {
    const out = spawnSync("py", ["-3", "-c", "import sys; print(sys.executable)"], {
      encoding: "utf8",
      windowsHide: true,
    });
    const exe = (out.stdout || "").trim();
    if (out.status === 0 && exe && fs.existsSync(exe) && !exe.toLowerCase().includes("windowsapps")) {
      return exe;
    }
  } catch (_) {
    /* ignore */
  }

  return "python";
}

function startPython() {
  if (process.env.JARVIS_NO_SPAWN === "1") {
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const logStream = fs.createWriteStream(LOG_FILE, { flags: "a" });
  logStream.write(`\n===== ${new Date().toISOString()} starting backend =====\n`);

  const py = resolvePython();
  logStream.write(`python=${py}\n`);

  pythonProc = spawn(py, ["-u", "main.py", "--ui-ws"], {
    cwd: PROJECT_ROOT,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env },
  });

  pythonProc.stdout.on("data", (chunk) => logStream.write(chunk));
  pythonProc.stderr.on("data", (chunk) => logStream.write(chunk));
  pythonProc.on("error", (err) => {
    logStream.write(`spawn error: ${err}\n`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("python-exit", -1);
    }
  });
  pythonProc.on("exit", (code) => {
    logStream.write(`exit code=${code}\n`);
    logStream.end();
    pythonProc = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("python-exit", code ?? 1);
    }
  });
}

function stopPython() {
  if (!pythonProc) return;
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(pythonProc.pid), "/T", "/F"]);
    } else {
      pythonProc.kill("SIGTERM");
    }
  } catch (_) {
    /* ignore */
  }
  pythonProc = null;
}

if (gotLock) {
  app.on("second-instance", () => {
    showWindow();
  });

  app.whenReady().then(() => {
    createWindow();
    createTray();
    startPython();
    connectBridgeSocket();

    app.on("activate", () => {
      showWindow();
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      isQuitting = true;
      stopPython();
      app.quit();
    }
  });

  app.on("before-quit", () => {
    isQuitting = true;
    stopPython();
  });

  ipcMain.handle("get-ws-url", () => WS_URL);
  ipcMain.handle("window-minimize", () => {
    if (mainWindow) mainWindow.minimize();
  });
  ipcMain.handle("window-close", () => {
    isQuitting = true;
    stopPython();
    if (mainWindow) mainWindow.close();
  });
}
