import React from 'react'
import {
  Play,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  Cpu,
  Zap,
  AlertTriangle
} from 'lucide-react'

const ExecutionPanel = ({ notebook, executionResults, activeCell }) => {
  const getExecutionStats = () => {
    if (!executionResults || Object.keys(executionResults).length === 0) {
      return { total: 0, successful: 0, failed: 0, totalTime: 0 }
    }

    const results = Object.values(executionResults)
    const total = results.length
    const successful = results.filter(r => r.success).length
    const failed = total - successful
    const totalTime = results.reduce((sum, r) => sum + (r.execution_time || 0), 0)

    return { total, successful, failed, totalTime }
  }

  const stats = getExecutionStats()
  const activeCellResult = executionResults[activeCell]

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-foreground flex items-center gap-2">
          <Cpu className="w-5 h-5 text-primary" />
          Execution Panel
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor cell execution and results
        </p>
      </div>

      {/* Stats */}
      <div className="p-4 border-b border-border">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-green-700">{stats.successful}</div>
                <div className="text-sm text-green-600">Successful</div>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-red-700">{stats.failed}</div>
                <div className="text-sm text-red-600">Failed</div>
              </div>
              <XCircle className="w-8 h-8 text-red-500" />
            </div>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-blue-700">{stats.total}</div>
                <div className="text-sm text-blue-600">Total Executed</div>
              </div>
              <Play className="w-8 h-8 text-blue-500" />
            </div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-purple-700">{stats.totalTime.toFixed(2)}s</div>
                <div className="text-sm text-purple-600">Total Time</div>
              </div>
              <Clock className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Active Cell Info (old) / Performance Tips & Active Cell Result (new) */}
      <div className="flex-1 overflow-auto p-4">
        <div className="mb-4">
          <h4 className="font-semibold text-sm text-foreground mb-2 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            Performance Tips
          </h4>
          <div className="space-y-2">
            <div className="bg-muted/50 border border-border rounded-lg p-3">
              <p className="text-xs font-medium text-foreground mb-1">Use vectorized operations</p>
              <p className="text-xs text-muted-foreground">
                Replace loops with pandas/numpy operations
              </p>
            </div>
            <div className="bg-muted/50 border border-border rounded-lg p-3">
              <p className="text-xs font-medium text-foreground mb-1">Limit data size</p>
              <p className="text-xs text-muted-foreground">
                Use .sample() or .head() for large datasets
              </p>
            </div>
            <div className="bg-muted/50 border border-border rounded-lg p-3">
              <p className="text-xs font-medium text-foreground mb-1">Cache results</p>
              <p className="text-xs text-muted-foreground">
                Store intermediate results in variables
              </p>
            </div>
          </div>
        </div>

        {/* Active Cell Result */}
        {activeCellResult && (
          <div className="mt-6">
            <h4 className="font-semibold text-sm text-foreground mb-2">Active Cell Result</h4>
            <div className={`rounded-lg p-3 border ${activeCellResult.success
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
              }`}>
              <div className="flex items-center gap-2 mb-2">
                {activeCellResult.success ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-600" />
                )}
                <span className={`text-sm font-medium ${activeCellResult.success ? 'text-green-700' : 'text-red-700'
                  }`}>
                  {activeCellResult.success ? 'Success' : 'Failed'}
                </span>
              </div>
              {activeCellResult.execution_time && (
                <p className="text-xs text-muted-foreground">
                  Executed in {activeCellResult.execution_time.toFixed(3)}s
                </p>
              )}
              {activeCellResult.error && (
                <p className="text-xs text-red-600 mt-2 font-mono">
                  {activeCellResult.error}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ExecutionPanel
  