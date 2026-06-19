import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQueries } from '@tanstack/react-query'
import { DollarSign, TrendingUp, PiggyBank, ArrowUpRight } from 'lucide-react'
import { expensesApi } from '@/api/expenses'
import { useExpenses, useCategorySummary } from '@/hooks/useExpenses'
import { useForecast } from '@/hooks/useForecast'
import { StatCard } from '@/components/shared/StatCard'
import { CategoryDonut } from '@/components/charts/CategoryDonut'
import { MonthlyTrendLine } from '@/components/charts/MonthlyTrendLine'
import { ForecastPreview } from '@/features/dashboard/ForecastPreview'
import { RecentTransactions } from '@/features/dashboard/RecentTransactions'
import { getCurrentMonth, getMonthsBack, formatCurrency } from '@/lib/utils'

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 } as const,
  },
} as const

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100, damping: 20 } },
} as const

export function DashboardPage() {
  const navigate = useNavigate()
  const currentMonth = getCurrentMonth()
  const months = getMonthsBack(6)

  const { data: expensesPage, isLoading: expensesLoading } = useExpenses({ skip: 0, limit: 8 })
  const { data: categorySummary, isLoading: catLoading } = useCategorySummary(currentMonth)
  const { data: forecast, isLoading: forecastLoading } = useForecast()

  const monthlyQueries = useQueries({
    queries: months.map((m) => ({
      queryKey: ['expenses', 'monthly-summary', m],
      queryFn: () => expensesApi.monthlySummary(m),
    })),
  })

  const topCategory = useMemo(() => {
    if (!categorySummary || categorySummary.length === 0) return null
    return categorySummary.reduce((max, c) => (c.total_amount > max.total_amount ? c : max), categorySummary[0])
  }, [categorySummary])

  const monthlyData = useMemo(() => {
    return monthlyQueries
      .filter((mq) => mq.data)
      .map((mq) => mq.data!)
      .sort((a, b) => a.month.localeCompare(b.month))
  }, [monthlyQueries])

  const currentMonthSummary = monthlyData.find((m) => m.month === currentMonth)
  const totalSpent = currentMonthSummary?.total_expenses ?? 0
  const totalIncome = currentMonthSummary?.total_income ?? 0
  const netSavings = totalIncome - totalSpent

  const statsLoading = monthlyQueries.some((mq) => mq.isLoading)

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={item}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Spent This Month"
            value={formatCurrency(totalSpent)}
            subtitle={currentMonth}
            icon={DollarSign}
            loading={statsLoading}
          />
          <StatCard
            title="Total Income"
            value={formatCurrency(totalIncome)}
            subtitle={currentMonth}
            icon={TrendingUp}
            trend={totalIncome > 0 ? 'up' : undefined}
            trendValue={totalIncome > 0 ? 'Income received' : undefined}
            loading={statsLoading}
          />
          <StatCard
            title="Net Savings"
            value={formatCurrency(netSavings)}
            subtitle={netSavings >= 0 ? 'Great month!' : 'Overspent'}
            icon={PiggyBank}
            trend={netSavings >= 0 ? 'up' : 'down'}
            trendValue={netSavings >= 0 ? 'Positive' : 'Negative'}
            loading={statsLoading}
          />
          <StatCard
            title="Top Category"
            value={topCategory?.category || 'N/A'}
            subtitle={topCategory ? formatCurrency(topCategory.total_amount) : undefined}
            icon={ArrowUpRight}
            loading={catLoading}
          />
        </div>
      </motion.div>

      <motion.div variants={item} className="grid gap-6 lg:grid-cols-2">
        <CategoryDonut data={categorySummary || []} loading={catLoading} />
        <MonthlyTrendLine data={monthlyData} loading={monthlyQueries.some((mq) => mq.isLoading)} />
      </motion.div>

      <motion.div variants={item} className="grid gap-6 lg:grid-cols-2">
        <ForecastPreview data={forecast || null} loading={forecastLoading} />
        <RecentTransactions
          expenses={expensesPage?.items || []}
          loading={expensesLoading}
          onViewAll={() => navigate('/expenses')}
          onUpload={() => navigate('/upload')}
        />
      </motion.div>
    </motion.div>
  )
}
