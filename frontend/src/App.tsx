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
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { useTheme } from '@/hooks/useTheme'
import { useAuthStore } from '@/store/auth-store'
import type { ReactNode } from 'react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function ProtectedApp() {
  return (
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
  )
}

function AppRoutes() {
  useTheme()

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <ProtectedApp />
            </RequireAuth>
          }
        />
      </Routes>
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
