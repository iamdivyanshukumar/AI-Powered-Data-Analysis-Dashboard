import React from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    })
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
          <div className="max-w-2xl w-full">
            <div className="text-center mb-8">
              <div className="inline-block p-4 bg-destructive/10 rounded-full mb-4">
                <AlertTriangle className="w-12 h-12 text-destructive" />
              </div>
              <h1 className="text-3xl font-bold text-foreground mb-2">
                Something went wrong
              </h1>
              <p className="text-muted-foreground">
                An unexpected error occurred. Don't worry, your work is safe.
              </p>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 mb-6">
              <h2 className="font-medium text-foreground mb-3">Error Details</h2>
              <div className="space-y-2">
                <div className="text-sm">
                  <span className="text-muted-foreground">Error: </span>
                  <code className="text-destructive">
                    {this.state.error?.toString() || 'Unknown error'}
                  </code>
                </div>
                {this.state.errorInfo?.componentStack && (
                  <details className="mt-4">
                    <summary className="text-sm text-muted-foreground cursor-pointer">
                      View technical details
                    </summary>
                    <pre className="mt-2 text-xs font-mono whitespace-pre-wrap bg-black/5 p-3 rounded overflow-auto max-h-64">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <Link
                to="/dashboard"
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-secondary text-secondary-foreground rounded-lg font-medium hover:bg-secondary/90 transition-colors"
              >
                <Home className="w-4 h-4" />
                Back to Dashboard
              </Link>
            </div>

            <div className="mt-6 text-center text-sm text-muted-foreground">
              <p>
                If the problem persists, please{' '}
                <button
                  onClick={() => window.location.reload()}
                  className="text-primary hover:text-primary/80"
                >
                  refresh the page
                </button>{' '}
                or contact support.
              </p>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary