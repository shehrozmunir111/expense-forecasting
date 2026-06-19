import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatMonth } from '@/lib/utils'
import type { MonthlySummary } from '@/types'

interface Props {
  data: MonthlySummary[]
  loading: boolean
}

export function MonthlyTrendLine({ data, loading }: Props) {
  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>Monthly Trend</CardTitle></CardHeader>
        <CardContent>
          <Skeleton className="h-56 w-full rounded-xl" />
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Monthly Trend</CardTitle></CardHeader>
        <CardContent>
          <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
            Insufficient data
          </div>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map((d) => ({
    month: formatMonth(d.month).split(' ')[0],
    Expenses: d.total_expenses,
    Income: d.total_income,
  }))

  return (
    <Card>
      <CardHeader><CardTitle>Monthly Trend</CardTitle></CardHeader>
      <CardContent>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" strokeOpacity={0.3} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
                axisLine={{ stroke: 'var(--color-border)', strokeOpacity: 0.3 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-popover)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '12px',
                  fontSize: '13px',
                }}
                formatter={(value) => formatCurrency(Number(value))}
              />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
              />
              <Line
                type="monotone"
                dataKey="Expenses"
                stroke="#FB7185"
                strokeWidth={2}
                dot={{ r: 3, fill: '#FB7185' }}
                activeDot={{ r: 5 }}
                isAnimationActive
                animationDuration={600}
              />
              <Line
                type="monotone"
                dataKey="Income"
                stroke="#4ADE80"
                strokeWidth={2}
                dot={{ r: 3, fill: '#4ADE80' }}
                activeDot={{ r: 5 }}
                isAnimationActive
                animationDuration={600}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
