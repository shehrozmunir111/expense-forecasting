import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { expensesApi } from '@/api/expenses'
import { useDataStore } from '@/store/data-store'
import type { ExpenseUpdate, ExpenseCreate, ExpensesListParams } from '@/types'
import toast from 'react-hot-toast'

export function useExpenses(params?: ExpensesListParams) {
  return useQuery({
    queryKey: ['expenses', params],
    queryFn: () => expensesApi.list(params),
  })
}

export function useExpense(id: number) {
  return useQuery({
    queryKey: ['expenses', id],
    queryFn: () => expensesApi.get(id),
    enabled: !!id,
  })
}

export function useUpdateExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ExpenseUpdate }) => expensesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success('Expense updated')
    },
  })
}

export function useDeleteExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => expensesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success('Expense deleted')
    },
  })
}

export function useCreateExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ExpenseCreate) => expensesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success('Expense created')
    },
  })
}

export function useUploadExpenses() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { expenses: ExpenseCreate[]; auto_categorize?: boolean }) => expensesApi.upload(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
    },
  })
}

export function useCategorySummary(month?: string) {
  return useQuery({
    queryKey: ['expenses', 'category-summary', month],
    queryFn: () => expensesApi.categorySummary(month),
  })
}

export function useMonthlySummary(month: string) {
  return useQuery({
    queryKey: ['expenses', 'monthly-summary', month],
    queryFn: () => expensesApi.monthlySummary(month),
  })
}

export function useRunCategorization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => expensesApi.runCategorization(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      useDataStore.getState().markMutated()
      toast.success('Categorization complete')
    },
  })
}
