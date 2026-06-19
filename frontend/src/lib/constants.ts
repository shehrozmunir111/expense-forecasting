export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const EXPENSE_CATEGORIES = [
  'Housing',
  'Transportation',
  'Food & Dining',
  'Utilities',
  'Insurance',
  'Healthcare',
  'Entertainment',
  'Shopping',
  'Education',
  'Travel',
  'Subscriptions',
  'Salary',
  'Freelance',
  'Investment',
  'Other Income',
  'Other Expense',
] as const

export const EXPENSE_STATUS = ['categorized', 'pending'] as const

export const CHAT_MODES = [
  { value: 'auto', label: 'Auto' },
] as const

export const PAGE_SIZE = 20
