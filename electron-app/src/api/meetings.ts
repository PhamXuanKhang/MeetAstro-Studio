/**
 * meetings.ts — FastAPI/Celery pipeline functions (kept after Supabase migration)
 *
 * ONLY contains functions that communicate with the FastAPI backend:
 * - createMeeting (for Celery pipeline)
 * - uploadMeetingMedia (audio upload → transcription job)
 * - startAnalysis (trigger GPT-4o analysis job)
 *
 * All CRUD read operations (list, get, delete) have been migrated
 * to src/api/supabase/ and consumed via React Query hooks.
 */

import { getClient, getCurrentUserId } from './client'
import type {
  AudioUploadResponse,
  StartAnalysisResponse,
} from '../types/supabase-models'

// --- Meeting creation (FastAPI → creates DB row + Celery-ready) ---

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

// --- Audio upload → transcription pipeline ---

export interface UploadMediaOptions {
  meetingId: string
  filePath: string
  fileBytes: ArrayBuffer
  diarize?: boolean
  language?: string
  signal?: AbortSignal
  onUploadProgress?: (pct: number) => void
}

/**
 * Upload audio/video and start transcription only (NOT analysis).
 * Target: POST /meetings/{id}/upload
 * Fallback: POST /meetings/{id}/audio
 */
export async function uploadMeetingMedia(opts: UploadMediaOptions): Promise<AudioUploadResponse> {
  const { meetingId, filePath, fileBytes, diarize = true, language = 'vi', signal } = opts

  const fileName = filePath.split(/[\\/]/).pop() ?? 'audio'
  const ext = fileName.split('.').pop()?.toLowerCase() ?? 'wav'
  const mimeMap: Record<string, string> = {
    wav: 'audio/wav', mp3: 'audio/mpeg', m4a: 'audio/mp4',
    ogg: 'audio/ogg', flac: 'audio/flac',
    mp4: 'video/mp4', mkv: 'video/x-matroska', webm: 'video/webm',
  }
  const blob = new Blob([fileBytes], { type: mimeMap[ext] ?? 'application/octet-stream' })
  const form = new FormData()
  form.append('file', blob, fileName)
  form.append('diarize', String(diarize))
  form.append('language', language)

  try {
    const { data } = await getClient().post<AudioUploadResponse>(
      `/meetings/${meetingId}/upload`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' }, signal, timeout: 30000 }
    )
    return data
  } catch (err: unknown) {
    // 404 means backend hasn't added /upload yet — fall back to /audio
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status !== 404) throw err

    const { data } = await getClient().post<AudioUploadResponse>(
      `/meetings/${meetingId}/audio`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' }, signal, timeout: 30000 }
    )
    return data
  }
}

// --- Analysis trigger ---

/**
 * Trigger analysis job (without polling).
 * Returns job_id for ProcessingView to track.
 */
export async function startAnalysis(meetingId: string): Promise<StartAnalysisResponse> {
  const { data } = await getClient().post<StartAnalysisResponse>(
    `/meetings/${meetingId}/analyze`
  )
  return data
}
