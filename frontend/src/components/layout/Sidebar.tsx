import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Receipt,
  Upload,
  TrendingUp,
  MessageSquare,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSidebarStore } from '@/store/sidebar-store'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/expenses', icon: Receipt, label: 'Expenses' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/forecast', icon: TrendingUp, label: 'Forecast' },
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const { expanded, mobileOpen, toggleExpanded, setMobileOpen } = useSidebarStore()
  const location = useLocation()

  const content = (
    <div
      className={cn(
        'flex h-full flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-300',
        expanded ? 'w-60' : 'w-16',
      )}
    >
      <div className="flex h-16 items-center justify-between px-4">
        <AnimatePresence mode="wait">
          {expanded ? (
            <motion.span
              key="logo"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-lg font-bold tracking-tight"
            >
              <span className="text-primary">Finance</span>Flow
            </motion.span>
          ) : (
            <motion.span
              key="logo-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-lg font-bold text-primary"
            >
              F
            </motion.span>
          )}
        </AnimatePresence>
        <button
          onClick={toggleExpanded}
          className="hidden lg:flex h-8 w-8 items-center justify-center rounded-xl hover:bg-sidebar-accent transition-colors"
          aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {expanded ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to))
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={cn('relative flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-colors', {
                'text-primary': isActive,
                'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent': !isActive,
              })}
            >
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-xl bg-primary/10"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              {isActive && (
                <motion.div
                  layoutId="sidebar-accent-bar"
                  className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-primary"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              <item.icon className="relative z-10 h-5 w-5 shrink-0" />
              <AnimatePresence mode="wait">
                {expanded && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="relative z-10 ml-3 overflow-hidden whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          )
        })}
      </nav>

      <div className="border-t border-border p-4">
        {expanded && (
          <p className="text-xs text-muted-foreground">FinanceFlow v2.0.5</p>
        )}
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex h-screen sticky top-0 flex-shrink-0 overflow-hidden">
        {content}
      </aside>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setMobileOpen(false)}
          >
            <motion.aside
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="h-full w-60 bg-sidebar text-sidebar-foreground border-r"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex h-16 items-center justify-between px-4">
                <span className="text-lg font-bold tracking-tight">
                  <span className="text-primary">Finance</span>Flow
                </span>
                <button
                  onClick={() => setMobileOpen(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-xl hover:bg-sidebar-accent"
                  aria-label="Close sidebar"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="space-y-1 px-3 py-4">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to))
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileOpen(false)}
                      className={cn('flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-colors', {
                        'text-primary bg-primary/10': isActive,
                        'text-muted-foreground hover:text-foreground hover:bg-sidebar-accent': !isActive,
                      })}
                    >
                      <item.icon className="h-5 w-5 shrink-0" />
                      <span className="ml-3">{item.label}</span>
                    </NavLink>
                  )
                })}
              </nav>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
