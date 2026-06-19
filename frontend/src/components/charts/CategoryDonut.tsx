import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency } from '@/lib/utils'
import type { CategorySummary } from '@/types'

const COLORS = ['#7C5CFC', '#4ADE80', '#FB7185', '#FBBF24', '#60A5FA', '#F472B6', '#34D399', '#A78BFA', '#F97316', '#06B6D4']

interface Props {
  data: CategorySummary[]
  loading: boolean
}

export function CategoryDonut({ data, loading }: Props) {
  const navigate = useNavigate()
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>By Category</CardTitle></CardHeader>
        <CardContent>
          <Skeleton className="h-56 w-full rounded-xl" />
        </CardContent>
      </Card>
    )
  }

  const filtered = data.filter((d) => d.total_amount > 0)

  if (filtered.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>By Category</CardTitle></CardHeader>
        <CardContent>
          <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
            No data this month
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader><CardTitle>By Category</CardTitle></CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="h-56 w-56 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={filtered}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="total_amount"
                  nameKey="category"
                  isAnimationActive
                  animationDuration={600}
                  onMouseEnter={(_, i) => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(null)}
                  onClick={(_data, index) => {
                    const item = filtered[index]
                    if (item) navigate(`/expenses?category=${encodeURIComponent(item.category)}`)
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {filtered.map((_, i) => (
                    <Cell
                      key={i}
                      fill={COLORS[i % COLORS.length]}
                      opacity={activeIndex === null || activeIndex === i ? 1 : 0.5}
                      stroke="transparent"
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-popover)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '12px',
                    fontSize: '13px',
                  }}
                  formatter={(value, name) => [formatCurrency(Number(value)), name]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-2">
            {filtered.slice(0, 6).map((d, i) => (
              <div key={d.category} className="flex items-center gap-2 text-sm">
                <div
                  className="h-3 w-3 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="flex-1 truncate">{d.category}</span>
                <span className="font-medium">{d.percentage.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
