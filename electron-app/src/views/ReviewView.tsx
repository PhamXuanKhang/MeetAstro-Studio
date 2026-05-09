import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'

interface Props {
  onNavigate: (route: string) => void
}

export default function ReviewView({ onNavigate }: Props) {
  const setMeetingDetailTab = useAppStore((s) => s.setMeetingDetailTab)

  useEffect(() => {
    setMeetingDetailTab('action_items')
    onNavigate('results')
  }, [onNavigate, setMeetingDetailTab])

  return (
    <div style={{ padding: 24, color: '#787671', fontSize: 13 }}>
      Đang mở tab Action Items...
    </div>
  )
}
