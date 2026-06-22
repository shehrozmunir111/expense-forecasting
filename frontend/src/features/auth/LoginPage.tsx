import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Wallet, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/auth-store'

const DEMO_EMAIL = 'demo@financeflow.local'
const DEMO_PASSWORD = 'demo12345'

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-sm rounded-2xl border bg-card p-8 shadow-sm"
      >
        <div className="mb-6 flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
            <Wallet className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-primary">Finance</span>Flow
          </span>
        </div>

        {/* Demo credentials box — sits ABOVE the "Sign in" heading */}
        <div className="mb-5 rounded-xl border border-primary/30 bg-primary/5 p-3.5 text-sm">
          <div className="mb-1.5 flex items-center gap-1.5 font-medium text-primary">
            <Info className="h-4 w-4" /> Try the demo account
          </div>
          <div className="space-y-0.5 font-mono text-xs text-muted-foreground">
            <div>Email: <span className="text-foreground">{DEMO_EMAIL}</span></div>
            <div>Password: <span className="text-foreground">{DEMO_PASSWORD}</span></div>
          </div>
          <button
            type="button"
            onClick={() => { setEmail(DEMO_EMAIL); setPassword(DEMO_PASSWORD) }}
            className="mt-2 text-xs font-medium text-primary hover:underline"
          >
            Fill demo credentials
          </button>
        </div>

        <h1 className="text-2xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">Continue to your dashboard.</p>

        {registered && (
          <div className="mt-4 rounded-xl border border-green-500/30 bg-green-500/10 px-3.5 py-2.5 text-sm text-green-600 dark:text-green-400">
            Account created. Please sign in.
          </div>
        )}
        {error && (
          <div className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm text-muted-foreground">Email</label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm text-muted-foreground">Password</label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
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
    </div>
  )
}
