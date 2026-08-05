const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jarvis", {
  getWsUrl: () => ipcRenderer.invoke("get-ws-url"),
  minimize: () => ipcRenderer.invoke("window-minimize"),
  close: () => ipcRenderer.invoke("window-close"),
  onPythonExit: (cb) => {
    ipcRenderer.on("python-exit", (_event, code) => cb(code));
  },
});
