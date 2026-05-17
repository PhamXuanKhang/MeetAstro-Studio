import { contextBridge, ipcRenderer } from 'electron'

// Detect PIP mode: main process passes --pip-mode via additionalArguments
const isPipMode = process.argv.includes('--pip-mode')

interface PipState {
  isRecording: boolean
  elapsedSeconds: number
  lastTranscriptLine?: string
}

interface LiveSegment {
  speaker: string
  start: number
  end: number
  text: string
}

interface AudioLevelEvent {
  source: string
  chunk_index: number
  bytes: number
  sys_rms: number
  sys_peak: number
  mic_rms: number
  mic_peak: number
  mixed_rms: number
  mixed_peak: number
  mic_queue: number
  mic_buffer: number
}

contextBridge.exposeInMainWorld('electronAPI', {
  // Audio recording
  startRecording: (config: Record<string, unknown>) =>
    ipcRenderer.invoke('audio:start', config),
  stopRecording: () =>
    ipcRenderer.invoke('audio:stop'),
  getRecordingStatus: () =>
    ipcRenderer.invoke('audio:status'),
  onStreamPartial: (callback: (segments: LiveSegment[]) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, segments: LiveSegment[]) => callback(segments)
    ipcRenderer.on('audio:streamPartial', listener)
    return () => ipcRenderer.removeListener('audio:streamPartial', listener)
  },
  onAudioLevel: (callback: (level: AudioLevelEvent) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, level: AudioLevelEvent) => callback(level)
    ipcRenderer.on('audio:level', listener)
    return () => ipcRenderer.removeListener('audio:level', listener)
  },

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

  // Auth deep links
  openExternalAuthUrl: (url: string) =>
    ipcRenderer.invoke('auth:openExternalUrl', url),
  onAuthDeepLink: (callback: (url: string) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, url: string) => callback(url)
    ipcRenderer.on('auth:deepLink', listener)
    return () => ipcRenderer.removeListener('auth:deepLink', listener)
  },

  // PIP mini-window
  isPipMode,
  openPip: (state: PipState) => ipcRenderer.invoke('pip:open', state),
  closePip: () => ipcRenderer.invoke('pip:close'),
  updatePipState: (state: PipState) => ipcRenderer.invoke('pip:updateState', state),
  pipStopRecording: () => ipcRenderer.invoke('pip:stopRecording'),
  pipFocusMain: () => ipcRenderer.invoke('pip:focusMain'),

  // Main renderer: listen for stop signal forwarded from PIP window
  onPipStopRequest: (callback: () => void) => {
    const listener = () => callback()
    ipcRenderer.on('recording:stopFromPip', listener)
    return () => ipcRenderer.removeListener('recording:stopFromPip', listener)
  },

  // PIP renderer: listen for state updates pushed from main process
  onPipStateUpdate: (callback: (state: PipState) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, state: PipState) => callback(state)
    ipcRenderer.on('pip:state', listener)
    return () => ipcRenderer.removeListener('pip:state', listener)
  },

  // Main renderer: notified when OS closes PIP window unexpectedly
  onPipClosed: (callback: () => void) => {
    const listener = () => callback()
    ipcRenderer.on('pip:closed', listener)
    return () => ipcRenderer.removeListener('pip:closed', listener)
  },
})
