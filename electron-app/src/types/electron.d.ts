export interface PipState {
  isRecording: boolean
  elapsedSeconds: number
  lastTranscriptLine?: string
}

export interface LiveSegment {
  speaker: string
  start: number
  end: number
  text: string
}

export interface RecordingStopStreamResult {
  job_id?: string
  transcript_source?: string
  persisted_segments?: number
  status?: string
}

export interface RecordingStopResponse {
  status: string
  output_path?: string
  error?: string
  stream_error?: string | null
  stream_result?: RecordingStopStreamResult
}

export interface ElectronAPI {
  startRecording: (config: Record<string, unknown>) => Promise<unknown>
  stopRecording: () => Promise<RecordingStopResponse>
  getRecordingStatus: () => Promise<unknown>
  onStreamPartial: (callback: (segments: LiveSegment[]) => void) => () => void
  openFileDialog: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  saveFile: (opts: { content: string; defaultName: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>
  readFileBytes: (filePath: string) => Promise<ArrayBuffer>
  getApiUrl: () => Promise<string>
  openExternalAuthUrl: (url: string) => Promise<void>
  onAuthDeepLink: (callback: (url: string) => void) => () => void
  // PIP mini-window
  isPipMode: boolean
  openPip: (state: PipState) => Promise<void>
  closePip: () => Promise<void>
  updatePipState: (state: PipState) => Promise<void>
  pipStopRecording: () => Promise<void>
  pipFocusMain: () => Promise<void>
  onPipStopRequest: (callback: () => void) => () => void
  onPipStateUpdate: (callback: (state: PipState) => void) => () => void
  onPipClosed: (callback: () => void) => () => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
