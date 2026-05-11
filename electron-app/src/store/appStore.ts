import { create } from 'zustand'
import type {
  MeetingAnalysis,
  MeetingResponse,
  ProcessingKind,
  ReviewItem,
  TranscriptSegment,
} from '../types/schema'

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
  currentJobId: string | null
  processingKind: ProcessingKind | null
  processingProgress: number | null
  processingMessage: string
  transcriptSegments: TranscriptSegment[]
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
  setAnalysis: (analysis: MeetingAnalysis | null) => void
  setSelectedMeeting: (meeting: MeetingResponse | null) => void
  setBusy: (busy: boolean, text?: string) => void
  setSearchQuery: (q: string) => void
  setCachedMeetings: (meetings: MeetingResponse[]) => void
  setReviewItems: (items: ReviewItem[]) => void
  setMeetingStatus: (status: string) => void
  setCurrentMeetingId: (id: string | null) => void
  setCurrentJobId: (id: string | null) => void
  setProcessingKind: (kind: ProcessingKind | null) => void
  setProcessingProgress: (progress: number | null) => void
  setProcessingMessage: (message: string) => void
  setTranscriptSegments: (segments: TranscriptSegment[]) => void
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
  analysis: null,
  selectedMeeting: null,
  progressText: '',
  busy: false,
  searchQuery: '',
  cachedMeetings: [],
  reviewItems: [],
  meetingStatus: '',
  currentMeetingId: null,
  currentJobId: null,
  processingKind: null,
  processingProgress: null,
  processingMessage: '',
  transcriptSegments: [],
  recordingPath: null,
  miniPopupOpen: false,
  selectedLanguage: 'vi',
  selectedDiarize: true,
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
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setProcessingKind: (processingKind) => set({ processingKind }),
  setProcessingProgress: (processingProgress) => set({ processingProgress }),
  setProcessingMessage: (processingMessage) => set({ processingMessage }),
  setTranscriptSegments: (transcriptSegments) => set({ transcriptSegments }),
  setRecordingPath: (recordingPath) => set({ recordingPath }),
  setMiniPopupOpen: (miniPopupOpen) => set({ miniPopupOpen }),
  setSelectedLanguage: (selectedLanguage) => set({ selectedLanguage }),
  setSelectedDiarize: (selectedDiarize) => set({ selectedDiarize }),

  // Reset per-meeting state when starting new meeting
  resetMeetingState: () =>
    set({
      audioPath: null,
      transcript: '',
      analysis: null,
      reviewItems: [],
      meetingStatus: '',
      currentMeetingId: null,
      currentJobId: null,
      processingKind: null,
      processingProgress: null,
      processingMessage: '',
      transcriptSegments: [],
      recordingPath: null,
      miniPopupOpen: false,
      isRecording: false,
    }),
}))
