import { create } from 'zustand'

interface SidebarState {
  expanded: boolean
  mobileOpen: boolean
  toggleExpanded: () => void
  setMobileOpen: (open: boolean) => void
}

export const useSidebarStore = create<SidebarState>((set) => ({
  expanded: true,
  mobileOpen: false,
  toggleExpanded: () => set((s) => ({ expanded: !s.expanded })),
  setMobileOpen: (open) => set({ mobileOpen: open }),
}))
