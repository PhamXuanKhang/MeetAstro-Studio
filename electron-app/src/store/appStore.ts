import { create } from 'zustand'
import type { ProcessingKind } from '../types/supabase-models'

// ─── Global UI State (React Query handles all API data caching) ──

export interface AppState {
  route: string
  isRecording: boolean
  audioPath: string | null
  transcript: string
  progressText: string
  busy: boolean
  searchQuery: string
  meetingStatus: string
  currentMeetingId: string | null
  currentMeetingTitle: string | null
  currentJobId: string | null
  processingKind: ProcessingKind | null
  processingProgress: number | null
  processingMessage: string
  processingDoneRoute: string | null
  recordingPath: string | null
  miniPopupOpen: boolean
  selectedLanguage: string
  selectedDiarize: boolean
}

interface AppActions {
  setRoute: (route: string) => void
  setIsRecording: (v: boolean) => void
  setAudioPath: (path: string | null) => void
  setTranscript: (text: string) => void
  setBusy: (busy: boolean, text?: string) => void
  setSearchQuery: (q: string) => void
  setMeetingStatus: (status: string) => void
  setCurrentMeetingId: (id: string | null) => void
  setCurrentMeetingTitle: (title: string | null) => void
  setCurrentJobId: (id: string | null) => void
  setProcessingKind: (kind: ProcessingKind | null) => void
  setProcessingProgress: (progress: number | null) => void
  setProcessingMessage: (message: string) => void
  setProcessingDoneRoute: (route: string | null) => void
  setRecordingPath: (path: string | null) => void
  setMiniPopupOpen: (open: boolean) => void
  setSelectedLanguage: (lang: string) => void
  setSelectedDiarize: (v: boolean) => void
  resetMeetingState: () => void
}

const initialState: AppState = {
  route: 'new_meeting',
  isRecording: false,
  audioPath: null,
  transcript: '',
  progressText: '',
  busy: false,
  searchQuery: '',
  meetingStatus: '',
  currentMeetingId: null,
  currentMeetingTitle: null,
  currentJobId: null,
  processingKind: null,
  processingProgress: null,
  processingMessage: '',
  processingDoneRoute: null,
  recordingPath: null,
  miniPopupOpen: false,
  selectedLanguage: '',
  selectedDiarize: true,
}

export const useAppStore = create<AppState & AppActions>((set) => ({
  ...initialState,

  setRoute: (route) => set({ route }),
  setIsRecording: (isRecording) => set({ isRecording }),
  setAudioPath: (audioPath) => set({ audioPath }),
  setTranscript: (transcript) => set({ transcript }),
  setBusy: (busy, text) => set({ busy, progressText: text ?? '' }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setMeetingStatus: (meetingStatus) => set({ meetingStatus }),
  setCurrentMeetingId: (currentMeetingId) => set({ currentMeetingId }),
  setCurrentMeetingTitle: (currentMeetingTitle) => set({ currentMeetingTitle }),
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setProcessingKind: (processingKind) => set({ processingKind }),
  setProcessingProgress: (processingProgress) => set({ processingProgress }),
  setProcessingMessage: (processingMessage) => set({ processingMessage }),
  setProcessingDoneRoute: (processingDoneRoute) => set({ processingDoneRoute }),
  setRecordingPath: (recordingPath) => set({ recordingPath }),
  setMiniPopupOpen: (miniPopupOpen) => set({ miniPopupOpen }),
  setSelectedLanguage: (selectedLanguage) => set({ selectedLanguage }),
  setSelectedDiarize: (selectedDiarize) => set({ selectedDiarize }),

  // Reset per-meeting state when starting new meeting
  resetMeetingState: () =>
    set({
      audioPath: null,
      transcript: '',
      meetingStatus: '',
      currentMeetingId: null,
      currentMeetingTitle: null,
      currentJobId: null,
      processingKind: null,
      processingProgress: null,
      processingMessage: '',
      processingDoneRoute: null,
      recordingPath: null,
      miniPopupOpen: false,
      isRecording: false,
    }),
}))
