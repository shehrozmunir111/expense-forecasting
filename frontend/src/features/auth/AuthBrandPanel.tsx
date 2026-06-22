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

// Brand CONTENT shown on the left (the page supplies the shared background).
export function AuthBrandPanel() {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="hidden max-w-lg lg:block"
    >
      {/* logo + small eyebrow directly beneath it */}
      <motion.div variants={item} className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/20">
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
      </motion.div>

      <motion.h1 variants={item} className="mt-8 text-[2.6rem] font-bold leading-[1.05] tracking-tight">
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

        {/* chat snippet — data matches the forecast card (Food & Dining $420) */}
        <motion.div
          variants={item}
          whileHover={{ y: -3 }}
          className="relative z-20 -mt-3 ml-auto w-[19rem] max-w-full rounded-2xl border bg-card/90 p-3.5 shadow-xl shadow-primary/5 backdrop-blur"
        >
          <div className="flex items-center gap-1.5 text-[11px] font-medium text-primary">
            <MessageSquare className="h-3.5 w-3.5" /> Chat with your finances
          </div>
          <p className="mt-2 text-sm text-foreground">"How much for Food &amp; Dining next month?"</p>
          <div className="mt-2 flex items-center gap-1.5 rounded-lg bg-primary/10 px-2.5 py-1.5 text-sm text-primary">
            <ArrowUpRight className="h-3.5 w-3.5" /> Forecast: <b className="font-semibold">$420</b> on Food &amp; Dining.
          </div>
        </motion.div>
      </div>

      {/* capability badges — lower, theme-colored */}
      <motion.div variants={item} className="mt-12 flex flex-wrap gap-x-6 gap-y-2 text-xs font-medium text-primary/80">
        <span className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> LLM-categorized</span>
        <span className="flex items-center gap-1.5"><TrendingUp className="h-3.5 w-3.5" /> Next-month forecast</span>
        <span className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Private per account</span>
      </motion.div>
    </motion.div>
  )
}
