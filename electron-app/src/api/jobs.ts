import { getClient } from './client'
import type { JobStatusResponse, JobState } from '../types/schema'

const TERMINAL_STATES: JobState[] = ['SUCCESS', 'FAILURE']

/**
 * Polls /jobs/{jobId} every intervalMs until SUCCESS or FAILURE,
 * or until timeoutMs is exceeded.
 * Mirrors HttpBackend._poll_job() in frontend/core/http_backend.py.
 */
export async function pollJob(
  jobId: string,
  timeoutMs: number = 180000,
  intervalMs: number = 2000,
  signal?: AbortSignal,
  onProgress?: (data: JobStatusResponse) => void
): Promise<JobStatusResponse> {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    if (signal?.aborted) {
      throw new DOMException('Job polling aborted', 'AbortError')
    }

    const { data } = await getClient().get<JobStatusResponse>(`/jobs/${jobId}`)
    onProgress?.(data)

    if (TERMINAL_STATES.includes(data.state)) {
      if (data.state === 'FAILURE') {
        throw new Error(`Job ${jobId} thất bại: ${data.error ?? 'unknown error'}`)
      }
      return data
    }

    await sleep(intervalMs, signal)
  }

  throw new Error(`Job ${jobId} timeout sau ${timeoutMs / 1000}s`)
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })
}
