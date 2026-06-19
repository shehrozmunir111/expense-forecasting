import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  MessageSquare,
  Trash2,
  Plus,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
  Split,
  Bot,
  Pencil,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useChat } from '@/hooks/useChat'
import type { ChatMessage } from '@/types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-2">
      <span className="typing-dot h-2 w-2 rounded-full bg-primary" />
      <span className="typing-dot h-2 w-2 rounded-full bg-primary" />
      <span className="typing-dot h-2 w-2 rounded-full bg-primary" />
    </div>
  )
}

function SourcePanel({ sources }: { sources: ChatMessage['sources'] }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Split className="h-3 w-3" />
        {sources.length} source{sources.length > 1 ? 's' : ''}
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {sources.map((s, i) => (
                <Card key={i} className="bg-muted/50">
                  <CardContent className="p-3">
                    <p className="text-xs font-medium">{s.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{s.detail}</p>
                    <Badge variant="secondary" className="mt-1 text-[10px]">{s.kind}</Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function HITLCard({
  message,
  onApprove,
  onReject,
}: {
  message: ChatMessage
  onApprove: () => void
  onReject: () => void
}) {
  if (message.status !== 'pending_approval' || !message.action) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className="mt-3 rounded-2xl border-2 border-warning/30 bg-warning/5 p-4"
    >
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="h-4 w-4 text-warning" />
        <span className="text-sm font-semibold">Action Required</span>
      </div>
      <p className="text-sm mb-3">{message.action.description}</p>
      <div className="flex gap-2">
        <Button size="sm" variant="default" onClick={onApprove}>
          <ThumbsUp className="mr-1 h-4 w-4" /> Approve
        </Button>
        <Button size="sm" variant="outline" onClick={onReject}>
          <ThumbsDown className="mr-1 h-4 w-4" /> Reject
        </Button>
      </div>
    </motion.div>
  )
}

export function ChatPage() {
  const {
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
  } = useChat()

  const [input, setInput] = useState('')
  const [editingNameId, setEditingNameId] = useState<string | null>(null)
  const [editNameValue, setEditNameValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasUnusedChat = conversations.some((c) => c.messages.length === 0)

  const pendingAction = activeConversation?.messages.findLast(
    (m) => m.status === 'pending_approval'
  )

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [activeConversation?.messages, scrollToBottom])

  const handleSend = async () => {
    const msg = input.trim()
    if (!msg || streaming) return
    setInput('')
    await sendMessage('auto', msg, activeId || undefined)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4 -mx-4 lg:-mx-8">
      {/* Conversation sidebar */}
      <div className="hidden md:flex w-64 flex-col shrink-0 border-r border-border px-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold">Conversations</h2>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => createConversation('auto')} disabled={hasUnusedChat} aria-label="New chat">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1 -mx-4 px-4">
          <div className="space-y-1">
            {conversations.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-8">No conversations yet</p>
            )}
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex items-center gap-1 px-3 py-2 rounded-xl text-sm transition-colors cursor-pointer ${
                  activeId === conv.id
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setActiveId(conv.id)}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                {editingNameId === conv.id ? (
                  <input
                    className="flex-1 bg-transparent border-b border-primary outline-none text-sm min-w-0"
                    value={editNameValue}
                    onChange={(e) => setEditNameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        renameConversation(conv.id, editNameValue.trim() || conv.title)
                        setEditingNameId(null)
                      }
                      if (e.key === 'Escape') setEditingNameId(null)
                    }}
                    onBlur={() => {
                      renameConversation(conv.id, editNameValue.trim() || conv.title)
                      setEditingNameId(null)
                    }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="truncate flex-1">{conv.title}</span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setEditingNameId(conv.id)
                    setEditNameValue(conv.title)
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Rename conversation"
                >
                  <Pencil className="h-3 w-3" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteConversation(conv.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive"
                  aria-label="Delete conversation"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </ScrollArea>
        <Separator className="my-4" />
        <Button variant="ghost" size="sm" onClick={clearAll} className="text-xs text-muted-foreground">
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          Clear all
        </Button>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 pr-2">
        {/* Header */}
        <div className="flex items-center mb-4">
          <h2 className="text-sm font-semibold">Chat</h2>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {!activeConversation ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-muted">
                <Bot className="h-10 w-10 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold">Start a conversation</h3>
              <p className="mt-1 text-sm text-muted-foreground max-w-sm">
                Ask about your expenses, get forecasts, or manage your finances
              </p>
              <div className="mt-6 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={hasUnusedChat}
                  onClick={() => createConversation('auto')}
                >
                  Start Chat
                </Button>
              </div>
            </div>
          ) : (
            activeConversation.messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role !== 'user' && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary text-xs">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card border border-border'
                    }`}
                  >
                    {msg.role === 'system' ? (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <AlertTriangle className="h-4 w-4" />
                        <span>{msg.content}</span>
                      </div>
                    ) : (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Metadata badges */}
                  <div className="flex items-center gap-2 mt-1.5 px-1">
                    {msg.role === 'assistant' && msg.status === 'completed' && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <CheckCircle className="h-3.5 w-3.5 text-success" />
                          </TooltipTrigger>
                          <TooltipContent>Response delivered</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                    {msg.routed_to && (
                      <Badge variant="secondary" className="text-[10px]">
                        Routed: {msg.routed_to}
                      </Badge>
                    )}
                    {msg.guardrails?.map((g, i) => (
                      <Badge key={i} variant="warning" className="text-[10px]">
                        {g}
                      </Badge>
                    ))}
                  </div>

                  {/* Sources */}
                  {msg.role === 'assistant' && <SourcePanel sources={msg.sources} />}
                </div>
                {msg.role === 'user' && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-muted text-xs">You</AvatarFallback>
                  </Avatar>
                )}
              </motion.div>
            ))
          )}

          {streaming && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/10 text-primary">
                  <Bot className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div className="rounded-2xl border border-border bg-card px-4 py-3">
                <TypingIndicator />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* HITL approval box above input */}
        {pendingAction && pendingAction.action && (
          <div className="mb-3">
            <HITLCard
              message={pendingAction}
              onApprove={() => activeId && approveAction(activeId, true)}
              onReject={() => activeId && approveAction(activeId, false)}
            />
          </div>
        )}

        {/* Input */}
        <div className="mt-4 flex items-end gap-2 border border-input rounded-2xl bg-card px-4 py-3 focus-within:ring-2 focus-within:ring-ring">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={pendingAction ? 'Approve or reject the action above...' : 'Ask about your finances...'}
            rows={1}
            className="flex-1 bg-transparent text-sm resize-none outline-none placeholder:text-muted-foreground max-h-32"
            disabled={streaming || !!pendingAction}
          />
          <Button
            size="icon"
            className="h-8 w-8 shrink-0 rounded-xl"
            onClick={handleSend}
            disabled={!input.trim() || streaming || !!pendingAction}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
