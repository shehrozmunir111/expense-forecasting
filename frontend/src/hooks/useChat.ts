import { useCallback } from 'react'
import { chatApi } from '@/api/chat'
import { useDataStore, type ConversationData } from '@/store/data-store'
import toast from 'react-hot-toast'
import type { ChatMessage, ChatSource } from '@/types'

const STORAGE_KEY = 'chat-conversations'

interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  mode: string
}

function mapSource(s: { kind?: string; label?: string; detail?: string; title?: string; content?: string; type?: string }): ChatSource {
  return {
    kind: s.kind || s.type || 'unknown',
    label: s.label || s.title || 'Source',
    detail: s.detail || s.content || '',
  }
}

const streamingModes = new Set(['rag', 'agent'])

const greetings = [
  'hi', 'hello', 'hey', 'greetings', 'hi there', 'hello there', 'hey there',
  'good morning', 'good afternoon', 'good evening', 'whats up', 'what\'s up',
  'how are you', 'howdy', 'sup', 'yo',
]

const greetingResponses = [
  "Hi! I'm your expense assistant. I can help you track spending, view forecasts, analyze categories, and manage your transactions. What would you like to know?",
  "Hello! How can I help you with your finances today? You can ask about your spending, categories, forecasts, or upload new expenses.",
  "Hey there! I'm here to help with your expense management. Try asking something like \"How much did I spend last month?\" or \"What's my forecast for next month?\"",
]

const irrelevantResponses = [
  "I'm designed to help with your expense tracking and financial forecasting. I can answer questions about your spending, categories, forecasts, and transactions. Try asking me something finance-related!",
  "I can only assist with expense management questions. Feel free to ask about your spending history, category breakdowns, future forecasts, or transaction details.",
]

function isGreeting(text: string): boolean {
  const lower = text.toLowerCase().trim().replace(/[^a-z\s']/g, '')
  return greetings.some((g) => lower === g || lower.startsWith(g + ' '))
}

function isUploadIntent(text: string): boolean {
  const lower = text.toLowerCase().trim()
  const uploadPhrases = [
    'upload', 'import', 'add new expense', 'add expense', 'new transaction',
    'add transaction', 'upload expense', 'import expense', 'upload csv',
    'upload file', 'import file', 'add new',
  ]
  return uploadPhrases.some((p) => lower.includes(p))
}

const uploadResponse =
  "You can upload new expenses by going to the **Upload** section in the sidebar. There you can drag-and-drop a CSV or JSON file, or add expenses manually."

// Clean up backend responses that contain LLM errors
function cleanLlmErrorResponse(content: string): string | null {
  const marker = "I couldn't reach the language model, but here's what your data shows:"
  if (!content.startsWith(marker)) return null
  const data = content.slice(marker.length).trim()
  const hasMonthlyData = /month \d{4}-\d{2}/i.test(data)
  const hasForecastData = /forecast|predict/i.test(data)
  const suggestion = hasForecastData
    ? '\n\nFor interactive forecast charts with confidence intervals, visit the **Forecast** page.'
    : hasMonthlyData
    ? '\n\nFor a visual category breakdown with charts, visit the **Dashboard** page.\nTo re-categorize expenses, go to the **Expenses** page and use the **Re-categorize** button.'
    : ''
  return data + suggestion
}

// Simple response cache: exact message → { content, cachedAt }
const responseCache = new Map<string, { content: string; cachedAt: number }>()

function isFinanceRelated(text: string): boolean {
  const keywords = [
    'expense', 'spend', 'spent', 'spending', 'cost', 'costs', 'costing',
    'money', 'finance', 'financial', 'budget', 'budgeting',
    'transaction', 'transactions', 'purchase', 'purchases', 'payment',
    'category', 'categories', 'forecast', 'forecasting', 'predict', 'prediction',
    'income', 'salary', 'revenue', 'earnings', 'saving', 'savings',
    'month', 'monthly', 'annual', 'year', 'yearly',
    'total', 'amount', 'much', 'chart', 'report',
    'bill', 'bills', 'subscription', 'subscriptions', 'groceries',
    'rent', 'utility', 'utilities', 'fuel', 'gas', 'dining',
    'upload', 'import', 'export', 'csv', 'file',
    'categorize', 'recategorize', 're-categorize', 'category',
    'delete', 'remove', 'edit', 'update', 'change',
  ]
  const lower = text.toLowerCase()
  return keywords.some((k) => lower.includes(k))
}

export function useChat() {
  const conversations = useDataStore((s) => s.conversations)
  const setConversations = useDataStore((s) => s.setConversations)
  const addStoreMessage = useDataStore((s) => s.addMessage)
  const activeId = useDataStore((s) => s.chatActiveId)
  const setActiveId = useDataStore((s) => s.setChatActiveId)
  const streaming = useDataStore((s) => s.chatStreaming)
  const setChatStreaming = useDataStore((s) => s.setChatStreaming)

  const activeConversation = conversations.find((c) => c.id === activeId) || null

  const createConversation = useCallback((mode: string) => {
    const id = crypto.randomUUID()
    const newConv: ConversationData = {
      id,
      title: `Chat ${new Date().toLocaleDateString()}`,
      messages: [],
      mode,
    }
    setConversations([newConv, ...conversations])
    setActiveId(id)
    return id
  }, [conversations, setConversations, setActiveId])

  const deleteConversation = useCallback((id: string) => {
    setConversations(conversations.filter((c) => c.id !== id))
    if (activeId === id) setActiveId(null)
  }, [conversations, setConversations, activeId, setActiveId])

  const renameConversation = useCallback((id: string, title: string) => {
    setConversations(conversations.map((c) => (c.id === id ? { ...c, title } : c)))
  }, [conversations, setConversations])

  const clearAll = useCallback(() => {
    setConversations([])
    setActiveId(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [setConversations, setActiveId])

  const sendMessage = useCallback(
    async (mode: string, message: string, convId?: string) => {
      const id = convId || createConversation(mode)

      // Add user message
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      }
      addStoreMessage(id, userMsg)

      // Handle greetings locally
      if (isGreeting(message)) {
        const reply = greetingResponses[Math.floor(Math.random() * greetingResponses.length)]
        addStoreMessage(id, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: reply,
          status: 'completed',
          timestamp: new Date().toISOString(),
        })
        return
      }

      // Handle upload intent locally → guide to Upload page
      if (isUploadIntent(message)) {
        addStoreMessage(id, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: uploadResponse,
          status: 'completed',
          timestamp: new Date().toISOString(),
        })
        return
      }

      // Handle non-finance queries locally
      if (!isFinanceRelated(message)) {
        const reply = irrelevantResponses[Math.floor(Math.random() * irrelevantResponses.length)]
        addStoreMessage(id, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: reply,
          status: 'completed',
          timestamp: new Date().toISOString(),
        })
        return
      }

      // Check cache for repeated question
      const cacheKey = message.toLowerCase().trim()
      const cached = responseCache.get(cacheKey)
      if (cached && cached.cachedAt > useDataStore.getState().lastMutatedAt) {
        addStoreMessage(id, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: cached.content,
          status: 'completed',
          timestamp: new Date().toISOString(),
        })
        return
      }

      // For API calls: show typing indicator, then add message when done
      setChatStreaming(true, id)

      try {
        if (streamingModes.has(mode)) {
          const url = chatApi.streamUrl(mode)
          const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, conversation_id: id }),
          })

          if (!response.ok) throw new Error('Stream failed')

          const reader = response.body?.getReader()
          const decoder = new TextDecoder()
          let content = ''

          if (reader) {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              const chunk = decoder.decode(value, { stream: true })
              content += chunk
            }
          }

          const cleaned = cleanLlmErrorResponse(content) ?? content
          addStoreMessage(id, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: cleaned,
            status: 'completed',
            timestamp: new Date().toISOString(),
          })
          responseCache.set(cacheKey, { content: cleaned, cachedAt: Date.now() })
        } else {
          const res = await chatApi.send(mode, { message, conversation_id: id })
          const guardrailFlags: string[] = []
          if (res.guardrails) {
            const g = res.guardrails as Record<string, unknown>
            Object.entries(g).forEach(([key, val]) => {
              if (val) guardrailFlags.push(key)
            })
          }
          const cleanedAnswer = cleanLlmErrorResponse(res.answer) ?? res.answer
          addStoreMessage(id, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: cleanedAnswer,
            sources: (res.sources || []).map(mapSource),
            grounded: res.grounded,
            guardrails: guardrailFlags.length > 0 ? guardrailFlags : undefined,
            routed_to: res.routed_to || undefined,
            status: res.status === 'pending_approval' ? 'pending_approval' : 'completed',
            action: res.pending
              ? {
                  type: String((res.pending as Record<string, unknown>).type || 'action'),
                  description: String((res.pending as Record<string, unknown>).description || ''),
                  expense_id: (res.pending as Record<string, unknown>).expense_id
                    ? Number((res.pending as Record<string, unknown>).expense_id)
                    : undefined,
                  suggested_category: (res.pending as Record<string, unknown>).suggested_category
                    ? String((res.pending as Record<string, unknown>).suggested_category)
                    : undefined,
                }
              : undefined,
            timestamp: new Date().toISOString(),
          })
          responseCache.set(cacheKey, { content: cleanedAnswer, cachedAt: Date.now() })
        }
      } catch {
        try {
          const res = await chatApi.send(mode, { message, conversation_id: id })
          const cleanedFallback = cleanLlmErrorResponse(res.answer) ?? res.answer
          addStoreMessage(id, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: cleanedFallback,
            sources: (res.sources || []).map(mapSource),
            grounded: res.grounded,
            status: 'completed',
            timestamp: new Date().toISOString(),
          })
          responseCache.set(cacheKey, { content: cleanedFallback, cachedAt: Date.now() })
        } catch {
          addStoreMessage(id, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: 'Sorry, something went wrong. Please try again.',
            status: 'completed',
            timestamp: new Date().toISOString(),
          })
        }
      } finally {
        setChatStreaming(false)
      }
    },
    [addStoreMessage, createConversation],
  )

  const approveAction = useCallback(
    async (convId: string, approved: boolean) => {
      try {
        const res = await chatApi.approve({ conversation_id: convId, approved })
        const convs = useDataStore.getState().conversations
        const updated = convs.map((c) => {
          if (c.id !== convId) return c
          const messages = [...c.messages]
          if (messages.length > 0) {
            messages[messages.length - 1] = { ...messages[messages.length - 1], status: approved ? 'approved' : 'rejected' }
          }
          messages.push({
            id: crypto.randomUUID(),
            role: 'system',
            content: res.message,
            timestamp: new Date().toISOString(),
          })
          return { ...c, messages }
        })
        setConversations(updated)
        toast.success(approved ? 'Action approved' : 'Action rejected')
      } catch {
        toast.error('Failed to process approval')
      }
    },
    [setConversations],
  )

  return {
    conversations,
    activeConversation,
    activeId,
    streaming,
    setActiveId,
    createConversation,
    deleteConversation,
    renameConversation,
    clearAll,
    sendMessage,
    approveAction,
  }
}