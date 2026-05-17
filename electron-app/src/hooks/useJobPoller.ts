import { useState, useEffect, useRef, useCallback } from 'react'
import { pollJob } from '../api/jobs'
import type { JobStatusResponse, JobState } from '../types/supabase-models'

interface UseJobPollerResult {
  isPolling: boolean
  jobState: JobState | null
  result: unknown
  error: string | null
  poll: (jobId: string, timeoutMs?: number) => Promise<JobStatusResponse>
  reset: () => void
}

/**
 * React hook wrapping pollJob with cleanup on unmount.
 * Mirrors HttpBackend._poll_job() pattern in frontend/core/http_backend.py.
 * Uses AbortController to cancel polling when component unmounts.
 */
export function useJobPoller(): UseJobPollerResult {
  const [isPolling, setIsPolling] = useState(false)
  const [jobState, setJobState] = useState<JobState | null>(null)
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const poll = useCallback(async (jobId: string, timeoutMs = 180000): Promise<JobStatusResponse> => {
    // Cancel any previous poll
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setIsPolling(true)
    setJobState('PENDING')
    setError(null)
    setResult(null)

    try {
      const final = await pollJob(
        jobId,
        timeoutMs,
        2000,
        controller.signal,
        (progress) => {
          setJobState(progress.state)
        }
      )
      setJobState(final.state)
      setResult(final.result)
      return final
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      throw err
    } finally {
      setIsPolling(false)
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setIsPolling(false)
    setJobState(null)
    setResult(null)
    setError(null)
  }, [])

  return { isPolling, jobState, result, error, poll, reset }
}
