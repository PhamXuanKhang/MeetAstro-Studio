export interface ElectronAPI {
  startRecording: (config: Record<string, unknown>) => Promise<unknown>
  stopRecording: () => Promise<unknown>
  getRecordingStatus: () => Promise<unknown>
  openFileDialog: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  saveFile: (opts: { content: string; defaultName: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>
  readFileBytes: (filePath: string) => Promise<ArrayBuffer>
  getApiUrl: () => Promise<string>
  openExternalAuthUrl: (url: string) => Promise<void>
  onAuthDeepLink: (callback: (url: string) => void) => () => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
