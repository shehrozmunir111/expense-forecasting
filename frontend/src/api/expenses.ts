import apiClient from './client'
import type { Expense, ExpenseCreate, ExpenseUpdate, PaginatedExpenses, CategorySummary, MonthlySummary, BulkUploadResponse, ExpensesListParams } from '@/types'

export const expensesApi = {
  list: (params?: ExpensesListParams) =>
    apiClient.get<PaginatedExpenses>('/expenses/', { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Expense>(`/expenses/${id}`).then((r) => r.data),

  create: (data: ExpenseCreate) =>
    apiClient.post<Expense>('/expenses/', data).then((r) => r.data),

  update: (id: number, data: ExpenseUpdate) =>
    apiClient.patch<Expense>(`/expenses/${id}`, data).then((r) => r.data),

  delete: (id: number) =>
    apiClient.delete(`/expenses/${id}`).then((r) => r.data),

  upload: (data: { expenses: ExpenseCreate[]; auto_categorize?: boolean }) =>
    apiClient.post<BulkUploadResponse>('/expenses/upload', data).then((r) => r.data),

  categorySummary: (month?: string) =>
    apiClient.get<CategorySummary[]>('/expenses/summary/by-category', { params: { month } }).then((r) => r.data),

  monthlySummary: (month: string) =>
    apiClient.get<MonthlySummary>('/expenses/summary/monthly', { params: { month } }).then((r) => r.data),

  runCategorization: () =>
    apiClient.post('/expenses/categorize/run').then((r) => r.data),
}
