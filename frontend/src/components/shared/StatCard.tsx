import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, type LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string
  subtitle?: string
  icon: LucideIcon
  trend?: 'up' | 'down'
  trendValue?: string
  loading?: boolean
}

export function StatCard({ title, value, subtitle, icon: Icon, trend, trendValue, loading }: StatCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 w-24 rounded-lg bg-muted" />
            <div className="h-8 w-32 rounded-lg bg-muted" />
            <div className="h-3 w-20 rounded-lg bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
    >
      <Card className="overflow-hidden transition-shadow hover:shadow-lg">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              <motion.p
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 100, damping: 20 }}
                className="text-2xl font-bold tracking-tight"
              >
                {value}
              </motion.p>
              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
              {trend && trendValue && (
                <div className="flex items-center gap-1 pt-1">
                  {trend === 'up' ? (
                    <TrendingUp className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-destructive" />
                  )}
                  <span className={cn('text-xs font-medium', trend === 'up' ? 'text-success' : 'text-destructive')}>
                    {trendValue}
                  </span>
                </div>
              )}
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
              <Icon className="h-6 w-6 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
