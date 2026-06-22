import type { ReactNode } from 'react'
import { Wallet } from 'lucide-react'
import { AuthBrandPanel } from './AuthBrandPanel'

// One continuous background (gradient + glow + dot grid) that spans the whole
// screen on every size. On large screens the full brand panel shows on the
// left; on small screens a compact brand header shows above the form so mobile
// gets the same branded look as desktop.
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-gradient-to-br from-primary/20 via-background to-background">
      {/* layered glow (positioned so some is visible on phones too) */}
      <div className="pointer-events-none absolute -left-20 -top-20 h-72 w-72 rounded-full bg-primary/25 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-16 top-1/4 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
      {/* dot grid, fading out */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(currentColor 1px, transparent 1px)',
          backgroundSize: '22px 22px',
          color: 'hsl(var(--muted-foreground) / 0.10)',
          maskImage: 'radial-gradient(ellipse at 30% 25%, black, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 30% 25%, black, transparent 75%)',
        }}
      />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-14 px-6 py-10 lg:flex-row lg:justify-between lg:px-12">
        <AuthBrandPanel />

        <div className="w-full max-w-sm">
          {/* compact brand header — only on small screens (brand panel is hidden there) */}
          <div className="mb-6 lg:hidden">
            <div className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/20">
                <Wallet className="h-4 w-4" />
              </span>
              <div className="leading-tight">
                <div className="text-base font-bold tracking-tight">
                  <span className="text-primary">Finance</span>Flow
                </div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary/80">
                  AI personal finance
                </div>
              </div>
            </div>
            <h2 className="mt-4 text-xl font-bold leading-tight tracking-tight">
              Know where your money goes —{' '}
              <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                and where it's going.
              </span>
            </h2>
          </div>

          {children}
        </div>
      </div>
    </div>
  )
}
