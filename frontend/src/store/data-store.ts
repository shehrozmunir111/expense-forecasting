import { create } from 'zustand'
import type { ChatMessage, ChatSource } from '@/types'

export type ConversationData = {
  id: string
  title: string
  messages: ChatMessage[]
  mode: string
}

interface DataState {
  lastMutatedAt: number
  markMutated: () => void
  chatStreaming: boolean
  chatStreamingConvId: string | null
  setChatStreaming: (streaming: boolean, convId?: string | null) => void
  chatActiveId: string | null
  setChatActiveId: (id: string | null) => void
  conversations: ConversationData[]
  setConversations: (convs: ConversationData[]) => void
  addMessage: (convId: string, msg: ChatMessage) => void
}

function loadConversations(): ConversationData[] {
  try {
    return JSON.parse(localStorage.getItem('chat-conversations') || '[]')
  } catch {
    return []
  }
}

function saveConversations(convs: ConversationData[]) {
  localStorage.setItem('chat-conversations', JSON.stringify(convs))
}

export const useDataStore = create<DataState>((set) => ({
  lastMutatedAt: 0,
  markMutated: () => set({ lastMutatedAt: Date.now() }),
  chatStreaming: false,
  chatStreamingConvId: null,
  setChatStreaming: (streaming, convId = null) => set({ chatStreaming: streaming, chatStreamingConvId: convId }),
  chatActiveId: null,
  setChatActiveId: (id) => set({ chatActiveId: id }),
  conversations: loadConversations(),
  setConversations: (convs) => {
    saveConversations(convs)
    set({ conversations: convs })
  },
  addMessage: (convId, msg) =>
    set((state) => {
      const updated = state.conversations.map((c) => {
        if (c.id !== convId) return c
        const messages = [...c.messages, msg]
        const title = c.messages.length === 0
          ? msg.content.slice(0, 48) + (msg.content.length > 48 ? '\u2026' : '')
          : c.title
        return { ...c, messages, title }
      })
      saveConversations(updated)
      return { conversations: updated }
    }),
}))
