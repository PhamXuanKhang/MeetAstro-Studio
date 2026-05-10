import { useCallback, useEffect, useRef, useState } from 'react'
import { useAppStore } from './store/appStore'
import { useAuthStore } from './store/authStore'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import BusyBanner from './components/BusyBanner'
import DashboardView from './views/DashboardView'
import MiniPopupView from './views/MiniPopupView'
import NewMeetingView from './views/NewMeetingView'
import ProcessingView from './views/ProcessingView'
import LiveRecordingView from './views/LiveRecordingView'
import ReviewTranscriptView from './views/ReviewTranscriptView'
import ResultsView from './views/ResultsView'
import ReviewView from './views/ReviewView'
import HistoryView from './views/HistoryView'
import SettingsView from './views/SettingsView'
import AuthLayout from './views/auth/AuthLayout'
import LoginView from './views/auth/LoginView'
import RegisterView from './views/auth/RegisterView'
import ForgotPasswordView from './views/auth/ForgotPasswordView'
import ResetPasswordView from './views/auth/ResetPasswordView'
import type { MeetingResponse } from './types/schema'
import type { MeetingListItem } from './types/supabase-models'

// Minimal shape accepted by openResults — compatible with both
// MeetingResponse (schema.ts) and MeetingItem (supabase-models.ts)
type OpenableMeeting = { id: string; title?: string | null; [key: string]: unknown }

type AuthRoute = 'login' | 'register' | 'forgot' | 'reset'

const ROUTE_TITLES: Record<string, string> = {
  home: 'Dashboard',
  new_meeting: 'Cuộc họp mới',
  live_recording: 'Đang ghi âm',
  processing: 'Đang xử lý',
  review_transcript: 'Review Transcript',
  results: 'Meeting Detail',
  review: 'Review & Push Jira',
  history: 'Lịch sử',
  settings: 'Cài đặt',
}

// PIP mode: main process passes --pip-mode via additionalArguments in webPreferences
const IS_PIP_MODE = window.electronAPI?.isPipMode === true

export default function App() {
  // Render minimal PIP view when running in the secondary always-on-top window
  if (IS_PIP_MODE) return <MiniPopupView />

  const { user, initialized, initializing, handleAuthCallback } = useAuthStore()
  const { route, setRoute, busy, progressText, searchQuery, setSearchQuery } = useAppStore()
  const { setSelectedMeeting, setAnalysis, setTranscript, setCurrentMeetingId } = useAppStore()
  const [authRoute, setAuthRoute] = useState<AuthRoute>('login')
  const [deepLinkError, setDeepLinkError] = useState<string | null>(null)

  const navigate = useCallback((r: string) => setRoute(r), [setRoute])

  useEffect(() => {
    if (!window.electronAPI?.onAuthDeepLink) return undefined
    return window.electronAPI.onAuthDeepLink(async (url) => {
      setDeepLinkError(null)
      const result = await handleAuthCallback(url)
      console.log('[auth] handleAuthCallback route:', result.route, 'hasError:', Boolean(result.error))
      if (result.route === 'reset') {
        setAuthRoute('reset')
        return
      }
      if (result.error) {
        console.error('[auth] deep-link error shown to user:', result.error)
        setDeepLinkError(result.error)
        setAuthRoute('login')
      }
    })
  }, [handleAuthCallback])

  const openResults = useCallback(
    (meeting: OpenableMeeting) => {
      // Cast to MeetingResponse for appStore compatibility (Phase 3 will unify types)
      setSelectedMeeting(meeting as unknown as MeetingResponse)
      setAnalysis(null)
      setTranscript('')
      setCurrentMeetingId(meeting.id)
      setRoute('results')
    },
    [setSelectedMeeting, setAnalysis, setTranscript, setCurrentMeetingId, setRoute]
  )

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleSearchChange = useCallback((q: string) => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setSearchQuery(q)
    }, 300)
  }, [setSearchQuery])

  const renderView = () => {
    switch (route) {
      case 'home':
        return <DashboardView onOpenResults={openResults} />
      case 'new_meeting':
        return <NewMeetingView />
      case 'live_recording':
        return <LiveRecordingView />
      case 'processing':
        return <ProcessingView />
      case 'review_transcript':
        return <ReviewTranscriptView />
      case 'results':
        return <ResultsView onNavigate={navigate} />
      case 'review':
        return <ReviewView onNavigate={navigate} />
      case 'history':
        return <HistoryView onOpenResults={openResults} />
      case 'settings':
        return <SettingsView />
      default:
        return <NewMeetingView />
    }
  }

  if (!initialized || initializing) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#f1f5f9' }}>
        <div style={{ width: 32, height: 32, border: '3px solid #0ea5e9', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (!user) {
    return (
      <AuthLayout>
        {deepLinkError && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
            <strong>Lỗi xác thực:</strong> {deepLinkError}
          </div>
        )}
        {authRoute === 'login' && (
          <LoginView
            onGoRegister={() => { setDeepLinkError(null); setAuthRoute('register') }}
            onGoForgot={() => { setDeepLinkError(null); setAuthRoute('forgot') }}
          />
        )}
        {authRoute === 'register' && (
          <RegisterView onGoLogin={() => { setDeepLinkError(null); setAuthRoute('login') }} />
        )}
        {authRoute === 'forgot' && (
          <ForgotPasswordView onGoLogin={() => { setDeepLinkError(null); setAuthRoute('login') }} />
        )}
        {authRoute === 'reset' && (
          <ResetPasswordView onDone={() => setAuthRoute('login')} />
        )}
      </AuthLayout>
    )
  }

  if (authRoute === 'reset') {
    return (
      <AuthLayout>
        <ResetPasswordView onDone={() => setAuthRoute('login')} />
      </AuthLayout>
    )
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#f8fafc' }}>
      <Sidebar currentRoute={route} onNavigate={navigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Topbar
          title={ROUTE_TITLES[route] ?? ''}
          searchValue={searchQuery}
          onSearchChange={handleSearchChange}
          onRecordClick={() => navigate('new_meeting')}
        />
        {busy && <BusyBanner text={progressText} />}
        <main style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {renderView()}
        </main>
      </div>
    </div>
  )
}
