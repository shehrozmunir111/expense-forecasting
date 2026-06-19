import { useState } from 'react'
import { motion } from 'framer-motion'
import { Moon, Sun, RotateCw, Database, Trash2, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { useTheme } from '@/hooks/useTheme'
import { useModelInfo } from '@/hooks/useForecast'
import { chatApi } from '@/api/chat'
import { API_BASE_URL } from '@/lib/constants'
import toast from 'react-hot-toast'

export function SettingsPage() {
  const { theme, toggleTheme } = useTheme()
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo()
  const [reindexing, setReindexing] = useState(false)

  const handleReindex = async () => {
    setReindexing(true)
    try {
      const res = await chatApi.reindex(true)
      toast.success(res.message || 'Reindexing complete')
    } catch {
      toast.error('Reindexing failed')
    } finally {
      setReindexing(false)
    }
  }

  const handleClearHistory = () => {
    localStorage.removeItem('chat-conversations')
    toast.success('Conversation history cleared')
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Customize your theme</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {theme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                <div>
                  <p className="text-sm font-medium">{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</p>
                  <p className="text-xs text-muted-foreground">Switch between dark and light themes</p>
                </div>
              </div>
              <Switch checked={theme === 'light'} onCheckedChange={toggleTheme} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Card>
          <CardHeader>
            <CardTitle>API Connection</CardTitle>
            <CardDescription>Backend endpoint configuration</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-muted">
                <Database className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Base URL</p>
                <code className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-lg">{API_BASE_URL}</code>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Card>
          <CardHeader>
            <CardTitle>Forecast Model</CardTitle>
            <CardDescription>ML model status and training info</CardDescription>
          </CardHeader>
          <CardContent>
            {modelLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-32" />
              </div>
            ) : modelInfo ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {modelInfo.ready_for_forecast ? (
                    <CheckCircle className="h-4 w-4 text-success" />
                  ) : (
                    <XCircle className="h-4 w-4 text-destructive" />
                  )}
                  <span className="text-sm">{modelInfo.ready_for_forecast ? 'Model is ready' : 'Need more data'}</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Categories Tracked</p>
                    <p className="text-sm font-medium">{modelInfo.categories_tracked.length}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Months of History</p>
                    <p className="text-sm font-medium">{modelInfo.months_of_history}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">Min Months Required</p>
                    <p className="text-sm font-medium">{modelInfo.min_months_required}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">Last Trained</p>
                    <p className="text-sm font-medium">
                      {modelInfo.last_trained
                        ? new Date(modelInfo.last_trained).toLocaleString()
                        : 'Never'}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Status</p>
                  <p className="text-sm">{modelInfo.status}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Failed to load model info</p>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Card>
          <CardHeader>
            <CardTitle>Maintenance</CardTitle>
            <CardDescription>Manage RAG index and data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RotateCw className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Reindex RAG</p>
                  <p className="text-xs text-muted-foreground">Rebuild the vector search index</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleReindex} disabled={reindexing}>
                <RotateCw className={`mr-1.5 h-4 w-4 ${reindexing ? 'animate-spin' : ''}`} />
                Reindex
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Trash2 className="h-5 w-5 text-destructive" />
                <div>
                  <p className="text-sm font-medium">Clear History</p>
                  <p className="text-xs text-muted-foreground">Delete all chat conversations</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleClearHistory}>
                <Trash2 className="mr-1.5 h-4 w-4" />
                Clear
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
