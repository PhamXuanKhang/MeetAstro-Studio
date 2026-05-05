import { useCallback } from 'react'
import { useAppStore } from './store/appStore'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import BusyBanner from './components/BusyBanner'
import DashboardView from './views/DashboardView'
import NewMeetingView from './views/NewMeetingView'
import ResultsView from './views/ResultsView'
import ReviewView from './views/ReviewView'
import HistoryView from './views/HistoryView'
import SettingsView from './views/SettingsView'
import type { MeetingResponse } from './types/schema'

const ROUTE_TITLES: Record<string, string> = {
  home: 'Dashboard',
  new_meeting: 'Cuộc họp mới',
  results: 'Kết quả phân tích',
  review: 'Review & Push Jira',
  history: 'Lịch sử',
  settings: 'Cài đặt',
}

export default function App() {
  const { route, setRoute, busy, progressText, searchQuery, setSearchQuery, setBusy } = useAppStore()
  const { setSelectedMeeting, setAnalysis, setTranscript, setCurrentMeetingId } = useAppStore()

  const navigate = useCallback((r: string) => setRoute(r), [setRoute])

  const openResults = useCallback(
    (meeting: MeetingResponse) => {
      setSelectedMeeting(meeting)
      setAnalysis(null)
      setTranscript('')
      setCurrentMeetingId(meeting.id)
      setRoute('results')
    },
    [setSelectedMeeting, setAnalysis, setTranscript, setCurrentMeetingId, setRoute]
  )

  // Search debounce (300ms) — mirrors threading.Timer(0.3) in frontend/app.py
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  const handleSearchChange = useCallback((q: string) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      setSearchQuery(q)
    }, 300)
  }, [setSearchQuery])

  const renderView = () => {
    switch (route) {
      case 'home':
        return <DashboardView onOpenResults={openResults} />
      case 'new_meeting':
        return (
          <NewMeetingView
            onOpenResults={openResults}
            onOpenReview={() => navigate('review')}
            setBusy={setBusy}
          />
        )
      case 'results':
        return <ResultsView onNavigate={navigate} />
      case 'review':
        return <ReviewView onNavigate={navigate} setBusy={setBusy} />
      case 'history':
        return <HistoryView onOpenResults={openResults} />
      case 'settings':
        return <SettingsView />
      default:
        return <NewMeetingView onOpenResults={openResults} onOpenReview={() => navigate('review')} setBusy={setBusy} />
    }
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
