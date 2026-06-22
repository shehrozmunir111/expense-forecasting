import type { ReactNode } from 'react'
import { AuthBrandPanel } from './AuthBrandPanel'

// One continuous background (gradient + glow + dot grid) that spans the whole
// screen. The brand content sits on the left and the auth form floats on the
// right over the SAME background — no hard 50/50 split.
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-gradient-to-br from-primary/15 via-background to-background">
      {/* layered glow */}
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 top-1/4 h-80 w-80 rounded-full bg-primary/15 blur-3xl" />
      {/* dot grid, fading out */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(currentColor 1px, transparent 1px)',
          backgroundSize: '22px 22px',
          color: 'hsl(var(--muted-foreground) / 0.10)',
          maskImage: 'radial-gradient(ellipse at 25% 30%, black, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 25% 30%, black, transparent 75%)',
        }}
      />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-14 px-6 lg:flex-row lg:justify-between lg:px-12">
        <AuthBrandPanel />
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  )
}
