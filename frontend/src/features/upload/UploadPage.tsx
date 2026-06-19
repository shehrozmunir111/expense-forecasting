import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, Plus, Trash2, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { useUploadExpenses } from '@/hooks/useExpenses'
import { EXPENSE_CATEGORIES } from '@/lib/constants'
import toast from 'react-hot-toast'
import type { ExpenseCreate } from '@/types'

interface ManualEntry {
  raw_text: string
  amount: string
  currency: string
  date: string
  is_income: string
}

const emptyEntry = (): ManualEntry => ({
  raw_text: '',
  amount: '',
  currency: 'USD',
  date: new Date().toISOString().split('T')[0],
  is_income: 'false',
})

export function UploadPage() {
  const navigate = useNavigate()
  const uploadMutation = useUploadExpenses()
  const [dragOver, setDragOver] = useState(false)
  const [autoCategorize, setAutoCategorize] = useState(true)
  const [entries, setEntries] = useState<ManualEntry[]>([emptyEntry()])
  const [file, setFile] = useState<File | null>(null)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(e.type === 'dragover')
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && (f.name.endsWith('.csv') || f.name.endsWith('.json'))) {
      setFile(f)
    } else {
      toast.error('Please upload a CSV or JSON file')
    }
  }, [])

  const addEntry = () => setEntries((prev) => [...prev, emptyEntry()])
  const removeEntry = (i: number) => setEntries((prev) => prev.filter((_, idx) => idx !== i))

  const updateEntry = (i: number, field: keyof ManualEntry, value: string) => {
    setEntries((prev) => prev.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)))
  }

  const validateEntries = (): ExpenseCreate[] => {
    const results: ExpenseCreate[] = []
    for (const e of entries) {
      const amount = parseFloat(e.amount)
      if (!e.raw_text.trim()) { toast.error('Description is required'); return [] }
      if (isNaN(amount) || amount <= 0) { toast.error('Amount must be a positive number'); return [] }
      if (!e.date) { toast.error('Date is required'); return [] }
      results.push({
        raw_text: e.raw_text.trim(),
        amount,
        currency: e.currency,
        date: e.date,
        is_income: e.is_income === 'true',
      })
    }
    return results
  }

  const handleUpload = async () => {
    if (file) {
      const text = await file.text()
      let expenses: ExpenseCreate[]
      if (file.name.endsWith('.json')) {
        const raw = JSON.parse(text)
        expenses = (Array.isArray(raw) ? raw : raw.expenses || []).map((r: Record<string, string>) => ({
          raw_text: r.raw_text || r.description || r.name || '',
          amount: parseFloat(r.amount || r.cost || '0'),
          currency: r.currency || 'USD',
          date: r.date || r.datetime || new Date().toISOString().split('T')[0],
          category: r.category || undefined,
          is_income: r.is_income === 'true' || r.type === 'income',
        }))
      } else {
        const lines = text.split('\n').filter(Boolean)
        const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
        expenses = lines.slice(1).map((line) => {
          const vals = line.split(',').map((v) => v.trim())
          const obj: Record<string, string> = {}
          headers.forEach((h, i) => { obj[h] = vals[i] || '' })
          return {
            raw_text: obj.raw_text || obj.description || obj.name || '',
            amount: parseFloat(obj.amount || obj.cost || '0'),
            currency: obj.currency || 'USD',
            date: obj.date || obj.datetime || new Date().toISOString().split('T')[0],
            category: obj.category || undefined,
            is_income: obj.is_income === 'true' || obj.type === 'income',
          }
        })
      }
      await uploadMutation.mutateAsync({ expenses, auto_categorize: autoCategorize })
      toast.success(`${expenses.length} expenses uploaded`)
      navigate('/expenses')
      return
    }

    const expenses = validateEntries()
    if (expenses.length === 0) return
    await uploadMutation.mutateAsync({ expenses, auto_categorize: autoCategorize })
    toast.success(`${expenses.length} expenses created`)
    navigate('/expenses')
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload Expenses</CardTitle>
          <CardDescription>Upload a CSV/JSON file or enter expenses manually</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="file">
            <TabsList className="mb-6">
              <TabsTrigger value="file">
                <FileText className="mr-1.5 h-4 w-4" />
                File Upload
              </TabsTrigger>
              <TabsTrigger value="manual">
                <Plus className="mr-1.5 h-4 w-4" />
                Manual Entry
              </TabsTrigger>
            </TabsList>

            <TabsContent value="file">
              <div
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
                  dragOver ? 'border-primary bg-primary/5' : 'border-border'
                }`}
              >
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-muted">
                  <Upload className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="text-sm font-medium">
                  {file ? file.name : 'Drop CSV or JSON here, or click to browse'}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Supports .csv and .json files
                </p>
                {file && (
                  <Button variant="outline" size="sm" className="mt-4" onClick={() => setFile(null)}>
                    Remove file
                  </Button>
                )}
                <Input
                  type="file"
                  accept=".csv,.json"
                  className="hidden"
                  id="file-upload"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) setFile(f)
                  }}
                />
                <label htmlFor="file-upload">
                  <Button variant="outline" size="sm" className="mt-4 cursor-pointer" asChild>
                    <span>Browse Files</span>
                  </Button>
                </label>
              </div>
            </TabsContent>

            <TabsContent value="manual" className="space-y-4">
              <AnimatePresence>
                {entries.map((entry, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="rounded-2xl border bg-muted/30 p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">Entry {i + 1}</span>
                      {entries.length > 1 && (
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeEntry(i)} aria-label="Remove entry">
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <Label className="text-xs">Description</Label>
                        <Input
                          value={entry.raw_text}
                          onChange={(e) => updateEntry(i, 'raw_text', e.target.value)}
                          placeholder="Coffee shop"
                          className="h-9 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Amount</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={entry.amount}
                          onChange={(e) => updateEntry(i, 'amount', e.target.value)}
                          placeholder="12.50"
                          className="h-9 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Currency</Label>
                        <Select value={entry.currency} onValueChange={(v) => updateEntry(i, 'currency', v)}>
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="USD">USD</SelectItem>
                            <SelectItem value="EUR">EUR</SelectItem>
                            <SelectItem value="GBP">GBP</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs">Date</Label>
                        <Input
                          type="date"
                          value={entry.date}
                          onChange={(e) => updateEntry(i, 'date', e.target.value)}
                          className="h-9 text-sm"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Type</Label>
                        <Select value={entry.is_income} onValueChange={(v) => updateEntry(i, 'is_income', v)}>
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="false">Expense</SelectItem>
                            <SelectItem value="true">Income</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              <Button variant="outline" size="sm" onClick={addEntry} className="w-full">
                <Plus className="mr-1.5 h-4 w-4" />
                Add Another Entry
              </Button>
            </TabsContent>
          </Tabs>

          <Separator className="my-6" />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch id="auto-cat" checked={autoCategorize} onCheckedChange={setAutoCategorize} />
              <Label htmlFor="auto-cat" className="text-sm">Auto-categorize</Label>
            </div>
            <Button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
              className="min-w-32"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-1.5 h-4 w-4" />
              )}
              {file ? 'Upload File' : `Upload ${entries.length} Entry${entries.length > 1 ? 'ies' : 'y'}`}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
