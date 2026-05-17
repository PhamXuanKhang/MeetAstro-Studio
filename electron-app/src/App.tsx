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
import { Icon } from './components/ui'

type AuthRoute = 'login' | 'register' | 'forgot' | 'reset'

const ROUTE_TITLES: Record<string, string> = {
  home: 'Dashboard',
  new_meeting: 'Cuộc họp mới',
  live_recording: 'Đang ghi âm',
  processing: 'Đang xử lý',
  review_transcript: 'Transcript',
  results: 'Kết quả phân tích',
  review: 'Review & Push Jira',
  history: 'Lịch sử',
  settings: 'Cài đặt',
}

const IS_PIP_MODE = window.electronAPI?.isPipMode === true

export default function App() {
  if (IS_PIP_MODE) return <MiniPopupView />

  const { user, initialized, initializing, handleAuthCallback } = useAuthStore()
  const { route, setRoute, busy, progressText, searchQuery, setSearchQuery, setBusy } = useAppStore()
  const { setCurrentMeetingId, setCurrentMeetingTitle, setTranscript } = useAppStore()
  const [authRoute, setAuthRoute] = useState<AuthRoute>('login')
  const [deepLinkError, setDeepLinkError] = useState<string | null>(null)

  const navigate = useCallback((r: string) => setRoute(r), [setRoute])

  useEffect(() => {
    if (!window.electronAPI?.onAuthDeepLink) return undefined
    return window.electronAPI.onAuthDeepLink(async (url) => {
      setDeepLinkError(null)
      const result = await handleAuthCallback(url)
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
    (meeting: { id: string; title?: string | null }) => {
      setCurrentMeetingId(meeting.id)
      setCurrentMeetingTitle(meeting.title ?? null)
      setTranscript('')
      setRoute('results')
    },
    [setCurrentMeetingId, setCurrentMeetingTitle, setTranscript, setRoute]
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
        return <ReviewView onNavigate={navigate} setBusy={setBusy} />
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
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg)', color: 'var(--color-primary)' }}>
        <Icon name="progress_activity" size={32} style={{ animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  if (!user) {
    return (
      <AuthLayout>
        {deepLinkError && (
          <div style={{ background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)', color: 'var(--color-danger)', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
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
    <div style={{ display: 'flex', height: '100vh', width: '100%', overflow: 'hidden', background: 'var(--color-bg)', position: 'relative', isolation: 'isolate' }}>
      <div className="landing-grid" style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />
      <Sidebar currentRoute={route} onNavigate={navigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, position: 'relative', zIndex: 1 }}>
        <Topbar
          title={ROUTE_TITLES[route] ?? ''}
          searchValue={searchQuery}
          onSearchChange={handleSearchChange}
          onRecordClick={() => navigate('new_meeting')}
        />
        {busy && <BusyBanner text={progressText} />}
        <main className="custom-scrollbar" style={{ flex: 1, overflowY: 'auto', padding: '24px 40px 40px' }}>
          {renderView()}
        </main>
      </div>
    </div>
  )
}
