import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import DashboardScreen from '@/screens/DashboardScreen'
import ReviewQueueScreen from '@/screens/ReviewQueueScreen'
import { Navigate } from 'react-router-dom'
import PipelineScreen from '@/screens/PipelineScreen'
import CalendarScreen from '@/screens/CalendarScreen'
import SessionScreen from '@/screens/SessionScreen'
import SettingsScreen from '@/screens/SettingsScreen'
import { applyTheme, useTheme } from '@/hooks/useTheme'

export default function App() {
  const theme = useTheme((s) => s.theme)
  useEffect(() => applyTheme(theme), [theme])

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardScreen />} />
          <Route path="review-queue" element={<ReviewQueueScreen />} />
          <Route path="jobs" element={<Navigate to="/review-queue" replace />} />
          <Route path="pipeline" element={<PipelineScreen />} />
          <Route path="calendar" element={<CalendarScreen />} />
          <Route path="session" element={<SessionScreen />} />
          <Route path="settings" element={<SettingsScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
