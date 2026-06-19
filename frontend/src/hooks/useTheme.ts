import { useEffect } from 'react'
import { useThemeStore } from '@/store/theme-store'

export function useTheme() {
  const { theme, toggleTheme, setTheme } = useThemeStore()

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'light') {
      root.classList.add('light')
    } else {
      root.classList.remove('light')
    }
  }, [theme])

  return { theme, toggleTheme, setTheme }
}
