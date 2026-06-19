import { Toaster as HotToaster } from 'react-hot-toast'
import { useThemeStore } from '@/store/theme-store'

export function Toaster() {
  const { theme } = useThemeStore()
  return (
    <HotToaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          borderRadius: '16px',
          padding: '12px 16px',
          fontSize: '14px',
          background: theme === 'dark' ? '#1a1a22' : '#ffffff',
          color: theme === 'dark' ? '#f1f1f6' : '#1a1a22',
          border: `1px solid ${theme === 'dark' ? '#2a2a35' : '#e5e7eb'}`,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        },
        success: {
          iconTheme: { primary: '#4ade80', secondary: '#ffffff' },
        },
        error: {
          iconTheme: { primary: '#fb7185', secondary: '#ffffff' },
        },
      }}
    />
  )
}
