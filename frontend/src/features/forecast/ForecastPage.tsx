import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, ErrorBar } from 'recharts'
import { motion } from 'framer-motion'
import { TrendingUp, RefreshCw, Brain } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton'
import { useForecast, useModelInfo, useTrainModel } from '@/hooks/useForecast'
import { formatCurrency, formatMonth } from '@/lib/utils'

function trendVariant(trend: string) {
  if (trend === 'increasing') return 'destructive' as const
  if (trend === 'decreasing') return 'success' as const
  return 'secondary' as const
}

function trendArrow(trend: string) {
  if (trend === 'increasing') return '↑'
  if (trend === 'decreasing') return '↓'
  return '→'
}

export function ForecastPage() {
  const { data, isLoading } = useForecast()
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo()
  const trainMutation = useTrainModel()

  const categories = data?.categories ?? []

  const chartData = categories.map((f) => {
    const low = f.confidence_interval_low ?? f.predicted_amount * 0.8
    const high = f.confidence_interval_high ?? f.predicted_amount * 1.2
    return {
      category: f.category,
      predicted: f.predicted_amount,
      lower: low,
      upper: high,
      errorY: [f.predicted_amount - low, high - f.predicted_amount],
    }
  })

  const maxVal = Math.max(...chartData.map((d) => d.upper), 1)

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                <Brain className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">ML Forecast Model</p>
                {modelLoading ? (
                  <Skeleton className="h-4 w-48 mt-1" />
                ) : modelInfo ? (
                  <div className="flex items-center gap-3 mt-0.5">
                    <Badge variant={modelInfo.ready_for_forecast ? 'success' : 'warning'}>
                      {modelInfo.ready_for_forecast ? 'Ready' : 'Need more data'}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {modelInfo.categories_tracked.length} categories · {modelInfo.months_of_history} months
                    </span>
                    {modelInfo.last_trained && (
                      <span className="text-xs text-muted-foreground">
                        Last trained: {new Date(modelInfo.last_trained).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                ) : null}
              </div>
            </div>
            <Button
              onClick={() => trainMutation.mutate()}
              disabled={trainMutation.isPending}
            >
              <RefreshCw className={`mr-1.5 h-4 w-4 ${trainMutation.isPending ? 'animate-spin' : ''}`} />
              Retrain
            </Button>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Card>
          <CardHeader>
            <CardTitle>Category Forecast</CardTitle>
            {data && (
              <CardDescription>
                Predicted spending for {formatMonth(data.forecast_month)} · {data.months_of_history} months of history ·
                Total: {formatCurrency(data.total_predicted)}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <LoadingSkeleton variant="chart" />
            ) : categories.length === 0 ? (
              <EmptyState
                icon={TrendingUp}
                title="Not enough data"
                description="Forecasting needs at least 2 months of expense data"
              />
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" strokeOpacity={0.3} />
                    <XAxis
                      dataKey="category"
                      tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
                      axisLine={{ stroke: 'var(--color-border)', strokeOpacity: 0.3 }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                      domain={[0, maxVal * 1.2]}
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
                    <Bar
                      dataKey="predicted"
                      fill="#7C5CFC"
                      radius={[8, 8, 0, 0]}
                      isAnimationActive
                      animationDuration={600}
                    >
                      {chartData.map((entry, i) => (
                        <ErrorBar
                          key={i}
                          dataKey="errorY"
                          stroke="#7C5CFC"
                          strokeWidth={2}
                          opacity={0.4}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {categories.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {categories.map((f, i) => {
            const low = f.confidence_interval_low ?? f.predicted_amount * 0.8
            const high = f.confidence_interval_high ?? f.predicted_amount * 1.2
            return (
              <motion.div
                key={f.category}
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
              >
                <Card>
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-medium">{f.category}</p>
                      <Badge variant={trendVariant(f.trend)}>
                        {trendArrow(f.trend)}
                      </Badge>
                    </div>
                    <p className="text-2xl font-bold">{formatCurrency(f.predicted_amount)}</p>
                    <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary/30"
                        style={{
                          width: `${((high - low) / (f.predicted_amount * 2)) * 100}%`,
                          marginLeft: `${Math.max(0, ((f.predicted_amount - low) / (f.predicted_amount * 2)) * 50)}%`,
                        }}
                      />
                    </div>
                    <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                      <span>{formatCurrency(low)}</span>
                      <span>{formatCurrency(high)}</span>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      )}
    </div>
  )
}
