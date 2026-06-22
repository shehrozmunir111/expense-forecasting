import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Wallet, Info, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/auth-store'
import { AuthLayout } from './AuthLayout'

const DEMO_EMAIL = 'demo@financeflow.local'
const DEMO_PASSWORD = 'demo12345'

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const registered = searchParams.get('registered')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await authApi.login(email, password)
      setAuth(data.access_token, data.user)
      navigate('/')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="w-full rounded-2xl border bg-card/95 p-7 shadow-2xl backdrop-blur"
        >
          {/* logo — shown on small screens where the brand panel is hidden */}
          <div className="mb-6 flex items-center gap-2.5 lg:hidden">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
              <Wallet className="h-5 w-5" />
            </span>
            <span className="text-lg font-bold tracking-tight">
              <span className="text-primary">Finance</span>Flow
            </span>
          </div>

          {/* Demo credentials box — sits ABOVE the "Sign in" heading */}
          <div className="mb-5 overflow-hidden rounded-xl border border-primary/30 bg-primary/5">
            <div className="flex items-center gap-1.5 border-b border-primary/20 bg-primary/10 px-3.5 py-2 text-sm font-medium text-primary">
              <Info className="h-4 w-4" /> Try the demo account
            </div>
            <div className="space-y-1 px-3.5 py-3">
              <div className="flex justify-between gap-3 font-mono text-xs">
                <span className="text-muted-foreground">email</span>
                <span className="text-foreground">{DEMO_EMAIL}</span>
              </div>
              <div className="flex justify-between gap-3 font-mono text-xs">
                <span className="text-muted-foreground">password</span>
                <span className="text-foreground">{DEMO_PASSWORD}</span>
              </div>
              <button
                type="button"
                onClick={() => { setEmail(DEMO_EMAIL); setPassword(DEMO_PASSWORD) }}
                className="mt-1 text-xs font-medium text-primary hover:underline"
              >
                Fill demo credentials →
              </button>
            </div>
          </div>

          <h1 className="text-2xl font-bold tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">Continue to your dashboard.</p>

          {registered && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-green-500/30 bg-green-500/10 px-3.5 py-2.5 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" /> Account created. Please sign in.
            </div>
          )}
          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm text-muted-foreground">Email</label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required />
            </div>
            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm text-muted-foreground">Password</label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">Sign up</Link>
          </p>
        </motion.div>
    </AuthLayout>
  )
}
