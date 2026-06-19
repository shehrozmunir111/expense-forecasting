import { create } from 'zustand'

interface ThemeState {
  theme: 'dark' | 'light'
  toggleTheme: () => void
  setTheme: (t: 'dark' | 'light') => void
}

const stored = (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'

export const useThemeStore = create<ThemeState>((set) => ({
  theme: stored,
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', next)
      return { theme: next }
    }),
  setTheme: (t) => {
    localStorage.setItem('theme', t)
    set({ theme: t })
  },
}))
