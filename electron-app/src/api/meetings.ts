import { getClient, getCurrentUserId } from './client'
import { pollJob } from './jobs'
import type {
  MeetingResponse,
  MeetingListResponse,
  AudioUploadResponse,
  TranscriptResponse,
  AnalysisResponse,
  JobStatusResponse,
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
