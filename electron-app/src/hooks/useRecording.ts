import { useState, useCallback, useRef, useEffect } from 'react'

interface RecordingStartResult {
  outputPath: string | null
  streaming: boolean
  streamError?: string
}

type ElectronAPI = {
  startRecording: (config: Record<string, unknown>) => Promise<{ status: string; output_path?: string; error?: string; streaming?: boolean; stream_error?: string }>
  stopRecording: () => Promise<{ status: string; output_path?: string; error?: string }>
  getRecordingStatus: () => Promise<{ isRecording: boolean; outputPath: string | null }>
}

function getElectronAPI(): ElectronAPI | null {
  return (window as unknown as { electronAPI?: ElectronAPI }).electronAPI ?? null
}

interface UseRecordingResult {
  isRecording: boolean
  outputPath: string | null
  error: string | null
  elapsedSeconds: number
  startRecording: (config?: Record<string, unknown>) => Promise<RecordingStartResult | null>
  stopRecording: () => Promise<string | null>
}

/**
 * Hook wrapping Python sidecar recording via Electron IPC.
 * Mirrors recording logic in frontend/views/new_meeting_view.py.
 * Provides elapsed time counter for UI display.
 */
export function useRecording(): UseRecordingResult {
  const [isRecording, setIsRecording] = useState(false)
  const [outputPath, setOutputPath] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  useEffect(() => {
    return () => clearTimer()
  }, [])

  const startRecording = useCallback(
    async (config: Record<string, unknown> = {}): Promise<RecordingStartResult | null> => {
      setError(null)
      setOutputPath(null)
      setElapsedSeconds(0)

      const api = getElectronAPI()
      if (!api) {
        setError('Electron API not available — recording requires the desktop app')
        return null
      }

      const defaultConfig = {
        sample_rate: 16000,
        channels: 1,
        mic_enabled: true,
        mic_gain: 3.0,
        sys_gain: 0.5,
        ...config,
      }

      const result = await api.startRecording(defaultConfig)
      if (result.error) {
        setError(result.error)
        return null
      }

      setIsRecording(true)
      // Timer: update elapsed every second
      timerRef.current = setInterval(() => {
        setElapsedSeconds((s) => s + 1)
      }, 1000)

      return {
        outputPath: result.output_path ?? null,
        streaming: Boolean(result.streaming),
        streamError: result.stream_error,
      }
    },
    []
  )

  const stopRecording = useCallback(async (): Promise<string | null> => {
    clearTimer()
    setIsRecording(false)

    const api = getElectronAPI()
    if (!api) return null

    const result = await api.stopRecording()
    if (result.error) {
      setError(result.error)
      return null
    }

    const path = result.output_path ?? null
    setOutputPath(path)
    return path
  }, [])

  return { isRecording, outputPath, error, elapsedSeconds, startRecording, stopRecording }
}
