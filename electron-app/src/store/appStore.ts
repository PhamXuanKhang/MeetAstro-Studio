import { create } from 'zustand'
import type { MeetingAnalysis, MeetingResponse, ReviewItem } from '../types/schema'

// Mirrors frontend/core/state.py AppState dataclass
export interface AppState {
  route: string
  isRecording: boolean
  audioPath: string | null
  transcript: string
  analysis: MeetingAnalysis | null
  selectedMeeting: MeetingResponse | null
  progressText: string
  busy: boolean
  searchQuery: string
  cachedMeetings: MeetingResponse[]
  reviewItems: ReviewItem[]
  meetingStatus: string
  currentMeetingId: string | null
}

interface AppActions {
  setRoute: (route: string) => void
  setIsRecording: (v: boolean) => void
  setAudioPath: (path: string | null) => void
  setTranscript: (text: string) => void
  setAnalysis: (analysis: MeetingAnalysis | null) => void
  setSelectedMeeting: (meeting: MeetingResponse | null) => void
  setBusy: (busy: boolean, text?: string) => void
  setSearchQuery: (q: string) => void
  setCachedMeetings: (meetings: MeetingResponse[]) => void
  setReviewItems: (items: ReviewItem[]) => void
  setMeetingStatus: (status: string) => void
  setCurrentMeetingId: (id: string | null) => void
  resetMeetingState: () => void
}

const initialState: AppState = {
  route: 'new_meeting',
  isRecording: false,
  audioPath: null,
  transcript: '',
  analysis: null,
  selectedMeeting: null,
  progressText: '',
  busy: false,
  searchQuery: '',
  cachedMeetings: [],
  reviewItems: [],
  meetingStatus: '',
  currentMeetingId: null,
}

export const useAppStore = create<AppState & AppActions>((set) => ({
  ...initialState,

  setRoute: (route) => set({ route }),
  setIsRecording: (isRecording) => set({ isRecording }),
  setAudioPath: (audioPath) => set({ audioPath }),
  setTranscript: (transcript) => set({ transcript }),
  setAnalysis: (analysis) => set({ analysis }),
  setSelectedMeeting: (selectedMeeting) => set({ selectedMeeting }),
  setBusy: (busy, text) => set({ busy, progressText: text ?? '' }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setCachedMeetings: (cachedMeetings) => set({ cachedMeetings }),
  setReviewItems: (reviewItems) => set({ reviewItems }),
  setMeetingStatus: (meetingStatus) => set({ meetingStatus }),
  setCurrentMeetingId: (currentMeetingId) => set({ currentMeetingId }),

  // Reset per-meeting state when starting new meeting
  resetMeetingState: () =>
    set({
      audioPath: null,
      transcript: '',
      analysis: null,
      reviewItems: [],
      meetingStatus: '',
      currentMeetingId: null,
      isRecording: false,
    }),
}))
