import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import DashboardScreen from '@/screens/DashboardScreen'
import ReviewQueueScreen from '@/screens/ReviewQueueScreen'
import ApplyQueueScreen from '@/screens/ApplyQueueScreen'
import ApplyRunsScreen from '@/screens/ApplyRunsScreen'
import { Navigate } from 'react-router-dom'
import PipelineScreen from '@/screens/PipelineScreen'
import CalendarScreen from '@/screens/CalendarScreen'
import SessionScreen from '@/screens/SessionScreen'
import SettingsLayout from '@/screens/settings/SettingsLayout'
import ProfileResumeScreen from '@/screens/settings/ProfileResumeScreen'
import SearchRolesScreen from '@/screens/settings/SearchRolesScreen'
import IntegrationsScreen from '@/screens/settings/IntegrationsScreen'
import AutomationScreen from '@/screens/settings/AutomationScreen'
import SystemScreen from '@/screens/settings/SystemScreen'
import SetupScreen from '@/screens/SetupScreen'
import { applyTheme, useTheme } from '@/hooks/useTheme'

export default function App() {
  const theme = useTheme((s) => s.theme)
  useEffect(() => applyTheme(theme), [theme])

  return (
    <BrowserRouter>
      <Routes>
        {/* First-run wizard renders without the AppShell (no sidebar/header). */}
        <Route path="setup" element={<SetupScreen />} />
        <Route element={<AppShell />}>
          <Route index element={<DashboardScreen />} />
          <Route path="review-queue" element={<ReviewQueueScreen />} />
          <Route path="apply-queue" element={<ApplyQueueScreen />} />
          <Route path="apply-runs" element={<ApplyRunsScreen />} />
          <Route path="jobs" element={<Navigate to="/review-queue" replace />} />
          <Route path="pipeline" element={<PipelineScreen />} />
          <Route path="calendar" element={<CalendarScreen />} />
          <Route path="session" element={<SessionScreen />} />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<Navigate to="profile" replace />} />
            <Route path="profile" element={<ProfileResumeScreen />} />
            <Route path="roles" element={<SearchRolesScreen />} />
            <Route path="integrations" element={<IntegrationsScreen />} />
            <Route path="automation" element={<AutomationScreen />} />
            <Route path="system" element={<SystemScreen />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
