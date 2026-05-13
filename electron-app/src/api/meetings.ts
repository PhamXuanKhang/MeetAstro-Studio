/**
 * meetings.ts - FastAPI/Celery pipeline functions.
 *
 * Supabase SDK handles lightweight meeting CRUD. FastAPI is used here for
 * upload, Celery job polling, and server-side AI actions.
 */

import { getClient, getCurrentUserId } from './client'
import type {
  AudioUploadResponse,
  JobStatusResponse,
  StartAnalysisResponse,
} from '../types/supabase-models'

export interface CreateMeetingResponse {
  id: string
  title: string
  status: string
  user_id: string
  created_at: string
  updated_at: string
}

export async function createMeeting(title: string, userId = getCurrentUserId()): Promise<CreateMeetingResponse> {
  const { data } = await getClient().post<CreateMeetingResponse>('/meetings', { title, user_id: userId })
  return data
}

export interface UploadMediaOptions {
  meetingId: string
  formData: FormData
  signal?: AbortSignal
  onUploadProgress?: (pct: number) => void
}

export function buildUploadFormData(opts: {
  filePath: string
  fileBytes: ArrayBuffer
  diarize?: boolean
  language?: string
}): FormData {
  const { filePath, fileBytes, diarize = true, language = 'vi' } = opts

  const fileName = filePath.split(/[\\/]/).pop() ?? 'audio'
  const ext = fileName.split('.').pop()?.toLowerCase() ?? 'wav'
  const mimeMap: Record<string, string> = {
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    m4a: 'audio/mp4',
    ogg: 'audio/ogg',
    mp4: 'video/mp4',
    mkv: 'video/x-matroska',
    webm: 'video/webm',
  }
  const fileUri = filePath.startsWith('file://')
    ? filePath
    : `file:///${filePath.replace(/\\/g, '/')}`

  const blob = new Blob([fileBytes], { type: mimeMap[ext] ?? 'application/octet-stream' })
  const form = new FormData()
  form.append('file', blob, fileName)
  form.append('client_path', fileUri)
  form.append('diarize', String(diarize))
  form.append('language', language)
  return form
}

/**
 * Upload audio/video and start the backend batch pipeline.
 * Backend currently runs transcribe + analyze, then writes results to Supabase.
 */
export async function uploadMeetingMedia(opts: UploadMediaOptions): Promise<AudioUploadResponse> {
  const { meetingId, formData, signal, onUploadProgress } = opts

  const { data } = await getClient().post<AudioUploadResponse>(
    `/meetings/${meetingId}/audio`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      signal,
      timeout: 300000,
      onUploadProgress: (event) => {
        if (!event.total) return
        onUploadProgress?.(Math.round((event.loaded * 100) / event.total))
      },
    }
  )
  return data
}

export async function pollJobStatus(jobId: string): Promise<JobStatusResponse> {
  const { data } = await getClient().get<JobStatusResponse>(`/jobs/${jobId}`)
  return data
}

export async function startAnalysis(meetingId: string): Promise<StartAnalysisResponse> {
  const { data } = await getClient().post<StartAnalysisResponse>(
    `/meetings/${meetingId}/analyze`
  )
  return data
}
