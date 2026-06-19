import { motion } from 'framer-motion'
import { ArrowRight, Receipt } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { formatCurrency, formatDate } from '@/lib/utils'
import type { Expense } from '@/types'

interface Props {
  expenses: Expense[]
  loading: boolean
  onViewAll: () => void
  onUpload: () => void
}

export function RecentTransactions({ expenses, loading, onViewAll, onUpload }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Transactions</CardTitle>
        <Button variant="ghost" size="sm" onClick={onViewAll}>
          View All <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-9 w-9 rounded-xl" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ) : expenses.length === 0 ? (
          <EmptyState
            icon={Receipt}
            title="No transactions yet"
            description="Upload your first expense to get started"
            action={{ label: 'Upload Expenses', onClick: onUpload }}
          />
        ) : (
          <div className="space-y-1">
            {expenses.map((exp, i) => (
              <motion.div
                key={exp.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ backgroundColor: 'var(--color-muted)', x: 2 }}
                className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors cursor-pointer"
              >
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-xl text-xs font-bold ${
                    exp.is_income
                      ? 'bg-success/10 text-success'
                      : 'bg-destructive/10 text-destructive'
                  }`}
                >
                  {exp.is_income ? '+' : '-'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{exp.raw_text}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(exp.date)}</p>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-semibold ${exp.is_income ? 'text-success' : ''}`}>
                    {exp.is_income ? '+' : '-'}{formatCurrency(exp.amount)}
                  </p>
                  {exp.category && (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                      {exp.category}
                    </Badge>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
