import { getClient, getCurrentUserId } from './client'
import { pollJob } from './jobs'
import type {
  AudioUploadResponse,
  AnalysisResponse,
  JobStatusResponse,
  MeetingListResponse,
  MeetingResponse,
  RenameSpeakerRequest,
  StartAnalysisResponse,
  TranscriptResponse,
  TranscriptSegment,
  TranscriptSegmentsResponse,
  UpdateTranscriptSegmentRequest,
} from '../types/schema'

// --- Meeting CRUD ---

export async function createMeeting(title: string, userId = getCurrentUserId()): Promise<MeetingResponse> {
  const { data } = await getClient().post<MeetingResponse>('/meetings', { title, user_id: userId })
  return data
}

export async function listMeetings(userId = getCurrentUserId(), page = 1, pageSize = 50): Promise<MeetingListResponse> {
  const { data } = await getClient().get<MeetingListResponse>('/meetings', {
    params: { user_id: userId, page, page_size: pageSize },
  })
  return data
}

export async function getMeeting(meetingId: string): Promise<MeetingResponse> {
  const { data } = await getClient().get<MeetingResponse>(`/meetings/${meetingId}`)
  return data
}

export async function deleteMeeting(meetingId: string): Promise<void> {
  await getClient().delete(`/meetings/${meetingId}`)
}

// --- Audio upload → transcription pipeline ---

/**
 * Upload audio file + poll until transcription done + return transcript.
 * Mirrors HttpBackend.transcribe() in frontend/core/http_backend.py.
 * multipart/form-data: file + diarize + language
 */
export async function uploadAndTranscribe(
  meetingId: string,
  filePath: string,
  fileBytes: ArrayBuffer,
  diarize = false,
  language = 'vi',
  signal?: AbortSignal,
  onProgress?: (job: JobStatusResponse) => void
): Promise<TranscriptResponse> {
  const fileName = filePath.split(/[\\/]/).pop() ?? 'audio.wav'
  const blob = new Blob([fileBytes], { type: 'audio/wav' })
  const form = new FormData()
  form.append('file', blob, fileName)
  form.append('diarize', String(diarize))
  form.append('language', language)

  const { data: uploadResp } = await getClient().post<AudioUploadResponse>(
    `/meetings/${meetingId}/audio`,
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    }
  )

  // Poll job (5 min timeout)
  await pollJob(uploadResp.job_id, 300000, 2000, signal, onProgress)

  // Fetch transcript
  const { data: transcript } = await getClient().get<TranscriptResponse>(
    `/meetings/${meetingId}/transcript`
  )
  return transcript
}

export async function getTranscript(meetingId: string): Promise<TranscriptResponse> {
  const { data } = await getClient().get<TranscriptResponse>(`/meetings/${meetingId}/transcript`)
  return data
}

export async function updateTranscript(meetingId: string, rawText: string): Promise<TranscriptResponse> {
  const { data } = await getClient().patch<TranscriptResponse>(
    `/meetings/${meetingId}/transcript`,
    { raw_text: rawText }
  )
  return data
}

// --- Analysis ---

/**
 * Trigger analysis → poll → return AnalysisResponse.
 * Mirrors HttpBackend.analyze() in frontend/core/http_backend.py.
 */
export async function analyzeTranscript(
  meetingId: string,
  signal?: AbortSignal,
  onProgress?: (job: JobStatusResponse) => void
): Promise<AnalysisResponse> {
  const { data: jobResp } = await getClient().post<JobStatusResponse>(
    `/meetings/${meetingId}/analyze`
  )

  await pollJob(jobResp.job_id, 180000, 2000, signal, onProgress)

  const { data: analysis } = await getClient().get<AnalysisResponse>(
    `/meetings/${meetingId}/analysis`
  )
  return analysis
}

export async function getAnalysis(meetingId: string): Promise<AnalysisResponse> {
  const { data } = await getClient().get<AnalysisResponse>(`/meetings/${meetingId}/analysis`)
  return data
}

// ─── Contract-first API (Phase 1.2) ──────────────────────────────────────────
// These functions target the Phase 1.2 contract endpoints. If backend isn't
// updated yet, they fall back to the legacy endpoint in isolation so that
// no UI component needs to know about the mismatch.

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
 * Fallback: POST /meetings/{id}/audio (backend may auto-run full pipeline)
 * Returns { meeting_id, job_id } for the caller to track via ProcessingView.
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

/**
 * Convert a blob TranscriptResponse into synthetic TranscriptSegments.
 * Used as a temporary fallback until backend returns real segments.
 */
function blobToSyntheticSegments(meetingId: string, blob: TranscriptResponse): TranscriptSegment[] {
  const text = blob.diarized_text ?? blob.raw_text
  if (!text?.trim()) return []

  const lines = text.split(/\n+/).filter((l) => l.trim())
  let cursor = 0
  return lines.map((line, i) => {
    const speakerMatch = line.match(/^(Speaker\s+\w+|[\w\s]+?):\s*(.+)$/)
    const speaker = speakerMatch ? speakerMatch[1].trim() : 'Speaker A'
    const content = speakerMatch ? speakerMatch[2].trim() : line.trim()
    const duration = Math.max(2, content.length * 0.06)
    const start = cursor
    cursor += duration
    return {
      id: `synthetic-${i}`,
      meeting_id: meetingId,
      speaker,
      start_time: Math.round(start * 100) / 100,
      end_time: Math.round(cursor * 100) / 100,
      content,
    }
  })
}

/**
 * Fetch transcript segments.
 * Target: GET /meetings/{id}/transcript/segments
 * Fallback: GET /meetings/{id}/transcript → convert blob to synthetic segments.
 */
export async function getTranscriptSegments(meetingId: string): Promise<TranscriptSegment[]> {
  try {
    const { data } = await getClient().get<TranscriptSegmentsResponse>(
      `/meetings/${meetingId}/transcript/segments`
    )
    return data.segments
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status !== 404) throw err

    // Fallback: fetch blob transcript and convert
    const { data: blob } = await getClient().get<TranscriptResponse>(
      `/meetings/${meetingId}/transcript`
    )
    return blobToSyntheticSegments(meetingId, blob)
  }
}

/**
 * Patch a single transcript segment.
 * Target: PATCH /meetings/{id}/transcript/segments/{segId}
 */
export async function updateTranscriptSegment(
  meetingId: string,
  segmentId: string,
  patch: UpdateTranscriptSegmentRequest
): Promise<TranscriptSegment> {
  if (segmentId.startsWith('synthetic-')) {
    // Synthetic segment — optimistic local update; backend not ready
    throw new Error('Segment editing requires backend transcript_segments support.')
  }
  const { data } = await getClient().patch<TranscriptSegment>(
    `/meetings/${meetingId}/transcript/segments/${segmentId}`,
    patch
  )
  return data
}

/**
 * Bulk rename all segments with a given speaker label.
 * Target: PUT /meetings/{id}/transcript/speakers
 */
export async function renameSpeaker(
  meetingId: string,
  req: RenameSpeakerRequest
): Promise<void> {
  await getClient().put(`/meetings/${meetingId}/transcript/speakers`, req)
}

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
