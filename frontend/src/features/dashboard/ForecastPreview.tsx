import { useNavigate } from 'react-router-dom'
import { ArrowRight, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { formatCurrency, formatMonth } from '@/lib/utils'
import type { ForecastResponse } from '@/types'

interface Props {
  data: ForecastResponse | null
  loading: boolean
}

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

export function ForecastPreview({ data, loading }: Props) {
  const navigate = useNavigate()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Forecast Preview</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => navigate('/forecast')}>
          Full Details <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : !data || !data.categories || data.categories.length === 0 ? (
          <EmptyState
            icon={TrendingUp}
            title="No forecast data"
            description="Add more expenses to generate predictions"
            action={{ label: 'Go to Forecast', onClick: () => navigate('/forecast') }}
          />
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Predicting for {formatMonth(data.forecast_month)} · {data.months_of_history} months of history
            </p>
            {data.categories.slice(0, 3).map((f) => {
              const low = f.confidence_interval_low ?? f.predicted_amount * 0.8
              const high = f.confidence_interval_high ?? f.predicted_amount * 1.2
              return (
                <div
                  key={f.category}
                  className="flex items-center justify-between rounded-xl bg-muted/50 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{f.category}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge variant={trendVariant(f.trend)}>
                        {trendArrow(f.trend)} {f.trend}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatCurrency(low)} – {formatCurrency(high)}
                      </span>
                    </div>
                  </div>
                  <p className="text-lg font-bold">{formatCurrency(f.predicted_amount)}</p>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
