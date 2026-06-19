import { Component, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-destructive/10">
            <AlertTriangle className="h-10 w-10 text-destructive" />
          </div>
          <h3 className="text-lg font-semibold">Something went wrong</h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <Button
            className="mt-6"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
          >
            <RefreshCw className="mr-1.5 h-4 w-4" />
            Reload page
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
