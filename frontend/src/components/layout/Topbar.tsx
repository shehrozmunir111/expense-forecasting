import { useLocation, useNavigate } from 'react-router-dom'
import { Moon, Sun, Menu, Search, LogOut } from 'lucide-react'
import { useThemeStore } from '@/store/theme-store'
import { useSidebarStore } from '@/store/sidebar-store'
import { useAuthStore } from '@/store/auth-store'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/expenses': 'Expenses',
  '/upload': 'Upload Expenses',
  '/forecast': 'Forecast',
  '/chat': 'Chat',
  '/settings': 'Settings',
}

export function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()
  const { setMobileOpen } = useSidebarStore()
  const { user, logout } = useAuthStore()

  const title = pageTitles[location.pathname] || 'Dashboard'
  const initials = (user?.full_name || user?.email || 'U').trim().charAt(0).toUpperCase()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/80 backdrop-blur-xl px-4 lg:px-8">
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden h-10 w-10 flex items-center justify-center rounded-xl hover:bg-accent transition-colors"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>

      <div className="hidden sm:flex relative ml-auto max-w-xs flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search expenses..." className="pl-9 h-9 text-sm rounded-xl bg-muted border-0" />
      </div>

      <button
        onClick={toggleTheme}
        className="h-10 w-10 flex items-center justify-center rounded-xl hover:bg-accent transition-colors"
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </button>

      <div className="flex items-center gap-2">
        {user?.email && (
          <span className="hidden md:block max-w-[160px] truncate text-sm text-muted-foreground" title={user.email}>
            {user.email}
          </span>
        )}
        <Avatar className="h-9 w-9">
          <AvatarFallback className="bg-primary/10 text-primary text-xs">{initials}</AvatarFallback>
        </Avatar>
        <button
          onClick={handleLogout}
          className="h-10 w-10 flex items-center justify-center rounded-xl hover:bg-accent transition-colors"
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </header>
  )
}
