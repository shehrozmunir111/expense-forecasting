import { motion } from 'framer-motion'
import { Wallet, TrendingUp, Sparkles, MessageSquare, ShieldCheck, ArrowUpRight } from 'lucide-react'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
}
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } },
}

const forecastRows = [
  { label: 'Food & Dining', amount: '$420', value: 82 },
  { label: 'Transportation', amount: '$290', value: 56 },
  { label: 'Subscriptions', amount: '$120', value: 24 },
]

// Left "thesis" panel beside the auth form on large screens — animated,
// layered, and product-showing so the page feels premium, never empty.
export function AuthBrandPanel() {
  return (
    <div className="relative hidden flex-col justify-between overflow-hidden border-r bg-gradient-to-br from-primary/15 via-background to-background p-12 lg:flex">
      {/* layered glow + dot grid */}
      <div className="pointer-events-none absolute -right-28 -top-28 h-80 w-80 rounded-full bg-primary/25 blur-3xl" />
      <div className="pointer-events-none absolute top-1/3 -left-24 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 right-10 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            'radial-gradient(currentColor 1px, transparent 1px)',
          backgroundSize: '22px 22px',
          color: 'hsl(var(--muted-foreground) / 0.12)',
          maskImage: 'radial-gradient(ellipse at 30% 20%, black, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 30% 20%, black, transparent 70%)',
        }}
      />

      <motion.div variants={container} initial="hidden" animate="show" className="relative flex h-full flex-col justify-between">
        <motion.div variants={item} className="flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
            <Wallet className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-primary">Finance</span>Flow
          </span>
        </motion.div>

        <div className="max-w-md">
          <motion.p variants={item} className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            AI personal finance
          </motion.p>
          <motion.h1 variants={item} className="mt-3 text-[2.6rem] font-bold leading-[1.05] tracking-tight">
            Know where your money goes —{' '}
            <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              and where it's going.
            </span>
          </motion.h1>
          <motion.p variants={item} className="mt-4 text-muted-foreground">
            Every transaction is auto-categorized by an LLM, a model forecasts next
            month per category, and you can just ask about your own money.
          </motion.p>

          {/* card stack */}
          <div className="relative mt-9">
            {/* forecast card */}
            <motion.div
              variants={item}
              whileHover={{ y: -3 }}
              className="relative z-10 max-w-sm rounded-2xl border bg-card/80 p-4 shadow-xl shadow-primary/5 backdrop-blur"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">Next month forecast</span>
                <span className="flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary">
                  <TrendingUp className="h-3 w-3" /> predicted
                </span>
              </div>
              <div className="mt-3 space-y-2.5">
                {forecastRows.map((row, i) => (
                  <div key={row.label}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-foreground">{row.label}</span>
                      <span className="font-mono text-muted-foreground">{row.amount}</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <motion.div
                        className="h-full rounded-full bg-primary"
                        initial={{ width: 0 }}
                        animate={{ width: `${row.value}%` }}
                        transition={{ duration: 0.9, delay: 0.5 + i * 0.15, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* chat snippet, overlapping below-right */}
            <motion.div
              variants={item}
              whileHover={{ y: -3 }}
              className="relative z-20 -mt-3 ml-auto w-[19rem] max-w-full rounded-2xl border bg-card/90 p-3.5 shadow-xl shadow-primary/5 backdrop-blur"
            >
              <div className="flex items-center gap-1.5 text-[11px] font-medium text-primary">
                <MessageSquare className="h-3.5 w-3.5" /> Chat with your finances
              </div>
              <p className="mt-2 text-sm text-foreground">"How much did I spend on food last month?"</p>
              <div className="mt-2 flex items-center gap-1.5 rounded-lg bg-primary/10 px-2.5 py-1.5 text-sm text-primary">
                <ArrowUpRight className="h-3.5 w-3.5" /> You spent <b className="font-semibold">$386</b> on Food &amp; Dining.
              </div>
            </motion.div>
          </div>
        </div>

        <motion.div variants={item} className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> LLM-categorized</span>
          <span className="flex items-center gap-1.5"><TrendingUp className="h-3.5 w-3.5" /> Next-month forecast</span>
          <span className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Private per account</span>
        </motion.div>
      </motion.div>
    </div>
  )
}
