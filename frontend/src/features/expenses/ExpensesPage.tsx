import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  RotateCw,
  Sparkles,
  Pencil,
  Trash2,
  Receipt,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { useExpenses, useDeleteExpense, useRunCategorization } from '@/hooks/useExpenses'
import { expensesApi } from '@/api/expenses'
import { useDataStore } from '@/store/data-store'
import { categorizeByKeywords } from '@/lib/categorize'
import { formatCurrency, formatDate } from '@/lib/utils'
import { EXPENSE_CATEGORIES, EXPENSE_STATUS, PAGE_SIZE } from '@/lib/constants'
import toast from 'react-hot-toast'
import type { Expense } from '@/types'

const statusMap: Record<string, string> = {
  pending: 'pending',
  categorized: 'categorized',
}

export function ExpensesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const page = Number(searchParams.get('page')) || 1
  const month = searchParams.get('month') || ''
  const category = searchParams.get('category') || ''
  const status = searchParams.get('status') || ''
  const search = searchParams.get('search') || ''

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editCategory, setEditCategory] = useState('')
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data, isLoading } = useExpenses({
    skip: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
    month: month || undefined,
    category: category || undefined,
    status: status || undefined,
    search: search || undefined,
  })
  const deleteMutation = useDeleteExpense()
  const categorizeMutation = useRunCategorization()
  const queryClient = useQueryClient()

  const totalPages = data ? Math.ceil(data.total / data.limit) : 1

  const updateSearch = useCallback((key: string, value: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value) next.set(key, value)
      else next.delete(key)
      if (key !== 'page') next.set('page', '1')
      return next
    })
  }, [setSearchParams])

  const handleEdit = (exp: Expense) => {
    setEditingId(exp.id)
    setEditCategory(exp.category || '')
  }

  const handleSaveEdit = async (id: number) => {
    try {
      await expensesApi.update(id, { category: editCategory || null })
      await queryClient.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success('Category updated')
      setEditingId(null)
    } catch {
      toast.error('Failed to update')
    }
  }

  const [clientCategorizing, setClientCategorizing] = useState(false)
  const handleClientCategorize = async () => {
    if (!data?.items || data.items.length === 0) return
    setClientCategorizing(true)
    let count = 0
    try {
      for (const exp of data.items) {
        const match = categorizeByKeywords(exp.raw_text || '')
        if (!match) continue
        const cat = (exp.category || '').toLowerCase().trim()
        if (cat !== 'other' && cat !== 'uncategorized' && cat !== '' && cat !== 'other expense' && cat !== 'other income') continue
        try {
          await expensesApi.update(exp.id, { category: match })
          count++
        } catch { /* skip individual failures */ }
      }
    } catch { /* skip */ }
    if (count > 0) {
      await queryClient.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success(`${count} expenses categorized`)
    } else {
      toast('No uncategorized expenses found on this page')
    }
    setClientCategorizing(false)
  }

  const statusBadgeVariant = (s: string) => {
    if (s === 'categorized') return 'success' as const
    return 'warning' as const
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Search..."
              value={search}
              onChange={(e) => updateSearch('search', e.target.value)}
              className="h-9 w-48 text-sm"
            />
            <Select value={month} onValueChange={(v) => updateSearch('month', v === 'all' ? '' : v)}>
              <SelectTrigger className="h-9 w-36 text-sm">
                <SelectValue placeholder="Month" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All months</SelectItem>
                {Array.from({ length: 12 }).map((_, i) => {
                  const d = new Date()
                  d.setMonth(d.getMonth() - i)
                  const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
                  return (
                    <SelectItem key={val} value={val}>
                      {d.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>
            <Select value={category} onValueChange={(v) => updateSearch('category', v === 'all' ? '' : v)}>
              <SelectTrigger className="h-9 w-40 text-sm">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {EXPENSE_CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={(v) => updateSearch('status', v === 'all' ? '' : v)}>
              <SelectTrigger className="h-9 w-36 text-sm">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All status</SelectItem>
                {EXPENSE_STATUS.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClientCategorize}
              disabled={clientCategorizing}
            >
              <Sparkles className={`mr-1.5 h-4 w-4 ${clientCategorizing ? 'animate-spin' : ''}`} />
              Auto-categorize
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => categorizeMutation.mutate()}
              disabled={categorizeMutation.isPending}
            >
              <RotateCw className={`mr-1.5 h-4 w-4 ${categorizeMutation.isPending ? 'animate-spin' : ''}`} />
              LLM Re-categorize
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Transactions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-xl" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              icon={Receipt}
              title="No expenses found"
              description="Try adjusting your filters or upload new expenses"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="text-left px-4 py-3 font-medium">Description</th>
                    <th className="text-left px-4 py-3 font-medium">Date</th>
                    <th className="text-left px-4 py-3 font-medium">Category</th>
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-center px-4 py-3 font-medium">Status</th>
                    <th className="text-right px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((exp, i) => (
                    <motion.tr
                      key={exp.id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      whileHover={{ backgroundColor: 'var(--color-muted)' }}
                      className="border-b border-border/50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-8 w-8 items-center justify-center rounded-xl text-xs font-bold ${
                            exp.is_income ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'
                          }`}>
                            {exp.is_income ? '+' : '-'}
                          </div>
                          <span className="font-medium">{exp.raw_text}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{formatDate(exp.date)}</td>
                      <td className="px-4 py-3">
                        {editingId === exp.id ? (
                          <div className="flex items-center gap-1">
                            <Select value={editCategory} onValueChange={setEditCategory}>
                              <SelectTrigger className="h-8 w-36 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {EXPENSE_CATEGORIES.map((c) => (
                                  <SelectItem key={c} value={c}>{c}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Button size="sm" variant="ghost" className="h-8" onClick={() => handleSaveEdit(exp.id)}>Save</Button>
                            <Button size="sm" variant="ghost" className="h-8" onClick={() => setEditingId(null)}>Cancel</Button>
                          </div>
                        ) : exp.category ? (
                          <Badge variant="secondary">{exp.category}</Badge>
                        ) : (
                          <span className="text-muted-foreground italic">Uncategorized</span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-right font-semibold ${exp.is_income ? 'text-success' : ''}`}>
                        {exp.is_income ? '+' : '-'}{formatCurrency(exp.amount)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={statusBadgeVariant(exp.categorization_status)}>
                          {exp.categorization_status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(exp)} aria-label="Edit">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => setDeleteId(exp.id)} aria-label="Delete">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages} ({data.total} total)
              </p>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => { updateSearch('page', String(page - 1)) }}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => { updateSearch('page', String(page + 1)) }}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteId !== null}
        onOpenChange={() => setDeleteId(null)}
        title="Delete Expense"
        description="Are you sure you want to delete this expense? This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => {
          if (deleteId) deleteMutation.mutate(deleteId)
          setDeleteId(null)
        }}
      />
    </div>
  )
}
