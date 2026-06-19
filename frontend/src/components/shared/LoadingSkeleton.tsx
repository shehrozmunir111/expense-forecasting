import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface LoadingSkeletonProps {
  className?: string
  count?: number
  variant?: 'card' | 'table-row' | 'chart' | 'text'
}

export function LoadingSkeleton({ className, count = 1, variant = 'card' }: LoadingSkeletonProps) {
  const items = Array.from({ length: count })

  if (variant === 'card') {
    return (
      <div className={cn('grid gap-4 sm:grid-cols-2 lg:grid-cols-4', className)}>
        {items.map((_, i) => (
          <div key={i} className="rounded-2xl border bg-card p-6">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'table-row') {
    return (
      <div className={cn('space-y-3', className)}>
        {items.map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-8 rounded-lg" />
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'chart') {
    return (
      <div className={cn('rounded-2xl border bg-card p-6', className)}>
        <Skeleton className="h-5 w-32 mb-4" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      {items.map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  )
}
