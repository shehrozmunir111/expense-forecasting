import apiClient from './client'
import { API_BASE_URL } from '@/lib/constants'
import type { ChatRequest, ChatResponse, ApprovalRequest, ApprovalResponse, ReindexResponse } from '@/types'

const modePaths: Record<string, string> = {
  auto: '/auto',
  rag: '',
  agent: '/agent',
  supervisor: '/supervisor',
  action: '/action',
}

function pathForMode(mode: string): string {
  return modePaths[mode] ?? `/${mode}`
}

export const chatApi = {
  send: (mode: string, data: ChatRequest) =>
    apiClient.post<ChatResponse>(`/chat${pathForMode(mode)}`, data).then((r) => r.data),

  approve: (data: ApprovalRequest) =>
    apiClient.post<ApprovalResponse>('/chat/approve', data).then((r) => r.data),

  reindex: (force = true) =>
    apiClient.post<ReindexResponse>('/chat/reindex', undefined, { params: { force } }).then((r) => r.data),

  streamUrl: (mode: string) => {
    const suffix = mode === 'rag' ? '/stream' : `${pathForMode(mode)}/stream`
    return `${API_BASE_URL}/chat${suffix}`
  },
}
