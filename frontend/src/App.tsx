import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/toast'
import { PageShell } from '@/components/layout/PageShell'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { ExpensesPage } from '@/features/expenses/ExpensesPage'
import { UploadPage } from '@/features/upload/UploadPage'
import { ForecastPage } from '@/features/forecast/ForecastPage'
import { ChatPage } from '@/features/chat/ChatPage'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { useTheme } from '@/hooks/useTheme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function AppRoutes() {
  useTheme()

  return (
    <BrowserRouter>
      <PageShell>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/expenses" element={<ExpensesPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      </PageShell>
    </BrowserRouter>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={300}>
        <AppRoutes />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
