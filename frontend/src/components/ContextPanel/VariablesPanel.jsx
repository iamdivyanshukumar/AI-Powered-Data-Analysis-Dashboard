import React, { useState, useEffect } from 'react'
import { useNotebook } from '../../contexts/NotebookContext'
import api from '../../services/api'
import { Variable, Database, Hash, Calendar, TrendingUp } from 'lucide-react'

const VariablesPanel = () => {
  const { currentSession } = useNotebook()
  const [variables, setVariables] = useState([])
  const [dataframeInfo, setDataframeInfo] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  // Fetch live variables from backend
  useEffect(() => {
    const fetchVariables = async () => {
      if (!currentSession?.session_id) return

      setIsLoading(true)
      try {
        const response = await api.getSessionVariables(currentSession.session_id)
        if (response.data.success) {
          setVariables(response.data.variables || [])
          setDataframeInfo(response.data.dataframe)
        }
      } catch (error) {
        console.error('Failed to fetch variables:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchVariables()

    // Poll every 3 seconds for updates
    const interval = setInterval(fetchVariables, 3000)
    return () => clearInterval(interval)
  }, [currentSession])

  const getVariableIcon = (varType) => {
    if (varType?.includes('DataFrame')) return <Database className="w-4 h-4 text-blue-500" />
    if (varType?.includes('int') || varType?.includes('float')) return <Hash className="w-4 h-4 text-green-500" />
    if (varType?.includes('datetime')) return <Calendar className="w-4 h-4 text-purple-500" />
    if (varType?.includes('list') || varType?.includes('dict')) return <TrendingUp className="w-4 h-4 text-orange-500" />
    return <Variable className="w-4 h-4 text-muted-foreground" />
  }

  if (isLoading && variables.length === 0) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-muted rounded w-3/4"></div>
          <div className="h-4 bg-muted rounded w-1/2"></div>
          <div className="h-4 bg-muted rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  if (!currentSession) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <Variable className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No active session</p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Main DataFrame Info */}
      {dataframeInfo && (
        <div className="bg-muted/30 rounded-lg p-3 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-primary" />
            <span className="font-medium text-sm">Main DataFrame</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-muted-foreground">Shape:</span>
              <span className="ml-1 font-mono">{dataframeInfo.shape?.[0]} × {dataframeInfo.shape?.[1]}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Memory:</span>
              <span className="ml-1 font-mono">{dataframeInfo.memory_mb?.toFixed(2)} MB</span>
            </div>
          </div>
          {dataframeInfo.columns && (
            <details className="mt-2">
              <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                {dataframeInfo.columns.length} columns
              </summary>
              <div className="mt-2 max-h-40 overflow-y-auto space-y-1">
                {dataframeInfo.columns.map((col, idx) => (
                  <div key={idx} className="text-xs font-mono flex items-center justify-between">
                    <span>{col}</span>
                    <span className="text-muted-foreground">{dataframeInfo.dtypes?.[col]}</span>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      {/* Python Variables */}
      <div>
        <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
          <Variable className="w-4 h-4" />
          Variables ({variables.length})
        </h3>

        {variables.length === 0 ? (
          <p className="text-xs text-muted-foreground">No variables yet. Execute a code cell to create variables.</p>
        ) : (
          <div className="space-y-2">
            {variables.map((variable, index) => (
              <div
                key={index}
                className="bg-card border border-border rounded-md p-2 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {getVariableIcon(variable.type)}
                    <span className="font-mono text-sm font-medium truncate">{variable.name}</span>
                  </div>
                  <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                    {variable.type}
                  </span>
                </div>
                {variable.value && (
                  <div className="mt-1 text-xs font-mono text-muted-foreground truncate">
                    {String(variable.value)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Live indicator */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span>Live updates</span>
      </div>
    </div>
  )
}

export default VariablesPanel