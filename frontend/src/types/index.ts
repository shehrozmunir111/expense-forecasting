export interface Expense {
  id: number
  raw_text: string
  amount: number
  currency: string
  date: string
  category: string | null
  category_confidence: number | null
  categorization_status: string
  source: string | null
  notes: string | null
  is_income: boolean
  created_at: string
  updated_at: string | null
}

export interface ExpenseCreate {
  raw_text: string
  amount: number
  currency: string
  date: string
  category?: string | null
  source?: string | null
  notes?: string | null
  is_income?: boolean
}

export interface ExpenseUpdate {
  category?: string | null
  notes?: string | null
  is_income?: boolean
}

export interface BulkUploadResponse {
  total_received: number
  stored: number
  categorization_status: string
  expense_ids: number[]
  message: string
}

export interface PaginatedExpenses {
  items: Expense[]
  total: number
  skip: number
  limit: number
}

export interface CategorySummary {
  category: string
  total_amount: number
  transaction_count: number
  currency: string
  percentage: number
}

export interface MonthlySummary {
  month: string
  total_expenses: number
  total_income: number
  net: number
  currency: string
  categories: CategorySummary[]
  transaction_count: number
}

export interface CategoryForecast {
  category: string
  predicted_amount: number
  currency: string
  confidence_interval_low: number | null
  confidence_interval_high: number | null
  trend: string
}

export interface ForecastResponse {
  forecast_month: string
  total_predicted: number
  currency: string
  categories: CategoryForecast[]
  model_info: Record<string, unknown>
  months_of_history: number
  generated_at: string
}

export interface ModelInfoResponse {
  status: string
  ready_for_forecast: boolean
  months_of_history: number
  categories_tracked: string[]
  last_trained: string | null
  min_months_required: number
  next_forecast_month: string | null
}

export interface TrainResponse {
  status: string
  message: string | null
  months_of_history: number | null
  categories_trained: string[] | null
  forecast_month: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  sources?: ChatSource[]
  grounded?: boolean
  guardrails?: string[]
  routed_to?: string
  status?: 'completed' | 'pending_approval' | 'blocked' | 'approved' | 'rejected'
  action?: PendingAction
  timestamp: string
}

export interface ChatSource {
  kind: string
  label: string
  detail: string
}

export interface PendingAction {
  type: string
  description: string
  expense_id?: number
  suggested_category?: string
}

export interface ChatRequest {
  message: string
  conversation_id?: string
  stream?: boolean
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
  conversation_id: string
  rewritten: boolean
  grounded: boolean
  guardrails: Record<string, unknown> | null
  status: string
  pending: Record<string, unknown> | null
  routed_to: string | null
}

export interface ApprovalRequest {
  conversation_id: string
  approved: boolean
}

export interface ApprovalResponse {
  status: string
  message: string
}

export interface ReindexResponse {
  status: string
  message: string
  chunks_reindexed?: number
}

export interface ExpensesListParams {
  skip?: number
  limit?: number
  month?: string
  category?: string
  status?: string
  is_income?: boolean
  search?: string
}
