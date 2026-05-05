import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // Audio recording
  startRecording: (config: Record<string, unknown>) =>
    ipcRenderer.invoke('audio:start', config),
  stopRecording: () =>
    ipcRenderer.invoke('audio:stop'),
  getRecordingStatus: () =>
    ipcRenderer.invoke('audio:status'),

  // File dialogs
  openFileDialog: (filters?: { name: string; extensions: string[] }[]) =>
    ipcRenderer.invoke('dialog:openFile', filters),
  saveFile: (opts: { content: string; defaultName: string; filters?: { name: string; extensions: string[] }[] }) =>
    ipcRenderer.invoke('dialog:saveFile', opts),

  // Local file access
  readFileBytes: (filePath: string) =>
    ipcRenderer.invoke('file:readBytes', filePath),

  // Config
  getApiUrl: () =>
    ipcRenderer.invoke('config:getApiUrl'),
})
